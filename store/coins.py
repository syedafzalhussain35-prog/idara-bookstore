from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    IKSCoinsSettings,
    IKSWallet,
    IKSWalletTransaction,
    Order,
    Review,
    UserProfile,
)


@dataclass
class _CoinDefaults:
    program_enabled: bool = True
    earn_percentage: Decimal = Decimal("5.00")
    max_coins_per_order: int = 100
    monthly_earning_cap: int = 300
    redemption_percentage_limit: int = 20
    minimum_cart_value: Decimal = Decimal("300.00")
    credit_delay_days: int = 7
    registration_bonus: int = 25
    first_purchase_bonus: int = 25
    review_bonus: int = 10
    profile_completion_bonus: int = 10
    disallow_with_coupon: bool = False


def get_coin_settings():
    settings_obj = IKSCoinsSettings.objects.filter(is_active=True).order_by("-updated_at", "-id").first()
    return settings_obj or _CoinDefaults()


def _month_key(now=None):
    now = now or timezone.now()
    return now.strftime("%Y-%m")


def get_wallet(user: User) -> IKSWallet:
    wallet, _ = IKSWallet.objects.get_or_create(user=user)
    key = _month_key()
    if wallet.month_key != key:
        wallet.month_key = key
        wallet.monthly_earned = 0
        wallet.save(update_fields=["month_key", "monthly_earned", "updated_at"])
    return wallet


def _eligible_profile(user: User) -> bool:
    if not user or not user.is_authenticated:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return bool(profile.iks_follow_instagram and profile.iks_follow_facebook)


def can_earn(user: User, wallet: Optional[IKSWallet] = None) -> bool:
    cfg = get_coin_settings()
    if not cfg.program_enabled:
        return False
    if not _eligible_profile(user):
        return False
    wallet = wallet or get_wallet(user)
    if wallet.is_frozen or wallet.is_earning_blocked:
        return False
    return True


def _coins_from_amount(amount: Decimal, percent: Decimal) -> int:
    if amount <= 0 or percent <= 0:
        return 0
    return int((amount * percent) / Decimal("100"))


def estimate_purchase_coins(user: User, amount: Decimal) -> int:
    wallet = get_wallet(user)
    if not can_earn(user, wallet):
        return 0
    cfg = get_coin_settings()
    base = _coins_from_amount(amount, Decimal(str(cfg.earn_percentage)))
    base = min(base, int(cfg.max_coins_per_order))
    remaining = max(int(cfg.monthly_earning_cap) - int(wallet.monthly_earned), 0)
    return max(min(base, remaining), 0)


def get_max_redeemable(wallet: IKSWallet, cart_total: Decimal) -> int:
    cfg = get_coin_settings()
    if not cfg.program_enabled or wallet.is_frozen:
        return 0
    if cart_total < Decimal(str(cfg.minimum_cart_value)):
        return 0
    percent_limit = int((cart_total * Decimal(int(cfg.redemption_percentage_limit))) / Decimal("100"))
    return max(min(wallet.balance, percent_limit), 0)


def _create_pending_tx(wallet: IKSWallet, order: Order, tx_type: str, coins: int, note: str, release_date):
    if coins <= 0:
        return None
    tx = IKSWalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        tx_type=tx_type,
        status="pending",
        coins=coins,
        amount=Decimal(coins),
        note=note,
        release_date=release_date,
    )
    wallet.pending_balance += coins
    wallet.save(update_fields=["pending_balance", "updated_at"])
    return tx


@transaction.atomic
def queue_order_pending_rewards(order: Order):
    if not order.user_id or not order.is_paid or order.status != "Delivered":
        return
    if order.coin_status in ("pending", "completed"):
        return
    user = order.user
    wallet = get_wallet(user)
    cfg = get_coin_settings()
    if not can_earn(user, wallet):
        return

    reward = estimate_purchase_coins(user, order.total_cost)
    release_date = timezone.now() + timezone.timedelta(days=int(cfg.credit_delay_days))
    if reward > 0:
        _create_pending_tx(
            wallet,
            order,
            "purchase_reward",
            reward,
            "Purchase reward pending release",
            release_date,
        )

    delivered_orders = Order.objects.filter(user=user, is_paid=True, status="Delivered").count()
    first_order = delivered_orders == 1
    if first_order and cfg.registration_bonus > 0:
        already = IKSWalletTransaction.objects.filter(wallet=wallet, tx_type="registration_bonus").exists()
        if not already:
            _create_pending_tx(
                wallet,
                order,
                "registration_bonus",
                int(cfg.registration_bonus),
                "Registration bonus (first purchase)",
                release_date,
            )
    if first_order and cfg.first_purchase_bonus > 0:
        already = IKSWalletTransaction.objects.filter(wallet=wallet, tx_type="first_purchase_bonus").exists()
        if not already:
            _create_pending_tx(
                wallet,
                order,
                "first_purchase_bonus",
                int(cfg.first_purchase_bonus),
                "First purchase bonus",
                release_date,
            )

    order.coin_status = "pending"
    order.coin_release_date = release_date
    order.coins_earned_estimate = reward
    order.coins_earned_final = reward
    order.save(update_fields=["coin_status", "coin_release_date", "coins_earned_estimate", "coins_earned_final"])


@transaction.atomic
def process_due_pending_rewards_for_user(user: User):
    wallet = IKSWallet.objects.filter(user=user).first()
    if not wallet:
        return
    due = wallet.transactions.select_related("order").filter(
        status="pending",
        release_date__isnull=False,
        release_date__lte=timezone.now(),
    )
    for tx in due:
        order = tx.order
        if order and order.status == "Cancelled":
            tx.status = "cancelled"
            tx.completed_at = timezone.now()
            tx.note = (tx.note or "") + " | Cancelled before release"
            tx.save(update_fields=["status", "completed_at", "note"])
            wallet.pending_balance = max(wallet.pending_balance - max(tx.coins, 0), 0)
            wallet.save(update_fields=["pending_balance", "updated_at"])
            if order.coin_status == "pending":
                order.coin_status = "cancelled"
                order.save(update_fields=["coin_status"])
            continue

        wallet.balance += max(tx.coins, 0)
        wallet.total_earned += max(tx.coins, 0)
        wallet.monthly_earned += max(tx.coins, 0)
        wallet.pending_balance = max(wallet.pending_balance - max(tx.coins, 0), 0)
        wallet.save(update_fields=["balance", "total_earned", "monthly_earned", "pending_balance", "updated_at"])

        tx.status = "completed"
        tx.completed_at = timezone.now()
        tx.save(update_fields=["status", "completed_at"])
        if order and order.coin_status == "pending":
            order.coin_status = "completed"
            order.save(update_fields=["coin_status"])


@transaction.atomic
def apply_redemption_for_order(order: Order) -> int:
    if not order.user_id or order.coins_redeemed <= 0:
        return 0
    wallet = get_wallet(order.user)
    if wallet.is_frozen:
        return 0
    if wallet.balance < order.coins_redeemed:
        return 0
    wallet.balance -= order.coins_redeemed
    wallet.total_redeemed += order.coins_redeemed
    wallet.save(update_fields=["balance", "total_redeemed", "updated_at"])
    IKSWalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        tx_type="redemption_deduction",
        status="completed",
        coins=-int(order.coins_redeemed),
        amount=Decimal(order.coins_redeemed),
        note="Coins redeemed at checkout",
        completed_at=timezone.now(),
    )
    return order.coins_redeemed


@transaction.atomic
def award_review_bonus_if_eligible(user: User, book):
    wallet = get_wallet(user)
    cfg = get_coin_settings()
    if not can_earn(user, wallet) or cfg.review_bonus <= 0:
        return 0
    existing = IKSWalletTransaction.objects.filter(
        wallet=wallet,
        tx_type="review_reward",
        book=book,
    ).exists()
    if existing:
        return 0
    if not Review.objects.filter(user=user, book=book).exists():
        return 0
    coins = int(cfg.review_bonus)
    wallet.balance += coins
    wallet.total_earned += coins
    wallet.monthly_earned += coins
    wallet.save(update_fields=["balance", "total_earned", "monthly_earned", "updated_at"])
    IKSWalletTransaction.objects.create(
        wallet=wallet,
        book=book,
        tx_type="review_reward",
        status="completed",
        coins=coins,
        amount=Decimal(coins),
        note="Review reward",
        completed_at=timezone.now(),
    )
    return coins


@transaction.atomic
def award_profile_completion_bonus_if_eligible(user: User):
    wallet = get_wallet(user)
    cfg = get_coin_settings()
    if not can_earn(user, wallet) or cfg.profile_completion_bonus <= 0:
        return 0
    already = IKSWalletTransaction.objects.filter(wallet=wallet, tx_type="profile_completion_reward").exists()
    if already:
        return 0
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not all([
        (user.first_name or "").strip(),
        (user.last_name or "").strip(),
        (profile.phone or "").strip(),
        (profile.address or "").strip(),
        (profile.city or "").strip(),
    ]):
        return 0
    coins = int(cfg.profile_completion_bonus)
    wallet.balance += coins
    wallet.total_earned += coins
    wallet.monthly_earned += coins
    wallet.save(update_fields=["balance", "total_earned", "monthly_earned", "updated_at"])
    IKSWalletTransaction.objects.create(
        wallet=wallet,
        tx_type="profile_completion_reward",
        status="completed",
        coins=coins,
        amount=Decimal(coins),
        note="Profile completion reward",
        completed_at=timezone.now(),
    )
    return coins


@transaction.atomic
def manual_adjust_wallet(wallet: IKSWallet, coins: int, note: str = ""):
    if coins == 0:
        return
    new_balance = wallet.balance + coins
    wallet.balance = max(new_balance, 0)
    if coins > 0:
        wallet.total_earned += coins
    else:
        wallet.total_redeemed += abs(coins)
    wallet.save(update_fields=["balance", "total_earned", "total_redeemed", "updated_at"])
    IKSWalletTransaction.objects.create(
        wallet=wallet,
        tx_type="manual_adjustment",
        status="completed",
        coins=coins,
        amount=Decimal(abs(coins)),
        note=note or "Manual admin adjustment",
        completed_at=timezone.now(),
    )
