from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.core.cache import cache

from .models import Banner, Book, Bundle, Cart, CartItem, CartBundleItem, Coupon, Order, Subject


@receiver(user_logged_in)
def merge_guest_cart(sender, request, user, **kwargs):
    cart_id = request.session.get("cart_id")
    if not cart_id:
        return

    guest_cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.select_related("book"):
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            book=item.book,
            defaults={"quantity": item.quantity},
        )
        if not created:
            user_item.quantity += item.quantity
            user_item.save()

    for bundle_item in guest_cart.bundle_items.select_related("bundle"):
        user_bundle, created = CartBundleItem.objects.get_or_create(
            cart=user_cart,
            bundle=bundle_item.bundle,
            defaults={"quantity": bundle_item.quantity},
        )
        if not created:
            user_bundle.quantity += bundle_item.quantity
            user_bundle.save()

    guest_cart.items.all().delete()
    guest_cart.bundle_items.all().delete()
    guest_cart.delete()
    request.session.pop("cart_id", None)
    request.session.modified = True

    if user.email:
        Order.objects.filter(user__isnull=True, email__iexact=user.email).update(user=user)


def _clear_home_cache():
    cache.delete_many([
        "home:banners:mobile",
        "home:banners:mobile:fallback",
        "home:banners:desktop",
        "home:featured",
        "home:bestsellers",
        "home:trending",
        "home:new_arrivals",
        "home:bundles",
        "home:subjects",
        "home:all_subjects",
        "home:popular",
    ])


@receiver(post_save, sender=Book)
@receiver(post_delete, sender=Book)
@receiver(post_save, sender=Subject)
@receiver(post_delete, sender=Subject)
@receiver(post_save, sender=Bundle)
@receiver(post_delete, sender=Bundle)
@receiver(post_save, sender=Coupon)
@receiver(post_delete, sender=Coupon)
@receiver(post_save, sender=Banner)
@receiver(post_delete, sender=Banner)
def clear_home_cache_on_updates(sender, **kwargs):
    _clear_home_cache()


@receiver(m2m_changed, sender=Bundle.books.through)
def clear_home_cache_on_bundle_book_change(sender, **kwargs):
    _clear_home_cache()
