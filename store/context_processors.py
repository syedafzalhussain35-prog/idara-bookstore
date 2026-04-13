from .models import Category, Cart, Book, Wishlist, SiteSettings
from django.db.models import Sum, Case, When, IntegerField
from django.conf import settings
from django.core.cache import cache
from .coins import get_wallet


NAV_CACHE_KEY = "cp:nav_categories:v1"
SITE_SETTINGS_CACHE_KEY = "cp:site_settings:v1"
CP_CACHE_TTL = int(getattr(settings, "CATEGORY_CACHE_TTL", 180))

def navbar_categories(request):
    """
    Exposes categories and cart count globally to all templates.
    """
    # Keep admin requests light; storefront-only widgets are not needed there.
    if request.path.startswith("/admin/"):
        return {
            "nav_categories": [],
            "cart_count": 0,
            "cart_preview_items": [],
            "cart_preview_total": 0,
            "cart_preview_empty": True,
            "cloudinary_base": "",
            "recently_viewed_books": [],
            "wishlist_preview_items": [],
            "wishlist_count": 0,
            "site_background_url": "",
            "site_loader_logo": "",
            "sales_offers_label": "Sales/Offers",
            "sales_offers_enabled": True,
            "coin_wallet": None,
        }

    # 1. Fetch Categories for the dropdown (cached)
    nav_categories = cache.get(NAV_CACHE_KEY)
    if nav_categories is None:
        nav_categories = list(
            Category.objects
            .only("name", "slug", "image")
            .all()
            .order_by("name")
        )
        cache.set(NAV_CACHE_KEY, nav_categories, CP_CACHE_TTL)

    # 2. Fetch Cart Count + Preview Items
    cart_count = 0
    cart_preview_items = []
    cart_preview_total = 0
    cart_preview_empty = True
    if request.user.is_authenticated:
        # Get the cart for the logged-in user
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            # Aggregate the sum of all item quantities in the cart
            result = cart.items.aggregate(total_qty=Sum('quantity'))
            cart_count = result.get('total_qty') or 0
            bundle_result = cart.bundle_items.aggregate(total_qty=Sum('quantity'))
            cart_count += bundle_result.get('total_qty') or 0
            cart_preview_empty = cart_count == 0
            if cart_count:
                cart_preview_items = list(
                    cart.items.select_related("book")
                    .order_by("-id")[:3]
                )
                cart_preview_total = cart.get_total()
    else:
        # For guest users, check if a cart_id exists in the session
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
            if cart:
                result = cart.items.aggregate(total_qty=Sum('quantity'))
                cart_count = result.get('total_qty') or 0
                bundle_result = cart.bundle_items.aggregate(total_qty=Sum('quantity'))
                cart_count += bundle_result.get('total_qty') or 0
                cart_preview_empty = cart_count == 0
                if cart_count:
                    cart_preview_items = list(
                        cart.items.select_related("book")
                        .order_by("-id")[:3]
                    )
                    cart_preview_total = cart.get_total()

    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') or ''
    cloudinary_base = f"https://res.cloudinary.com/{cloud_name}" if cloud_name else ""
    recently_viewed_books = []
    recent_ids = request.session.get("recently_viewed", [])[:5]
    if recent_ids:
        preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(recent_ids)], output_field=IntegerField())
        recently_viewed_books = list(Book.objects.filter(id__in=recent_ids).order_by(preserved))

    wishlist_preview_items = []
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_qs = Wishlist.objects.select_related("book").filter(user=request.user).order_by("-id")
        wishlist_count = wishlist_qs.count()
        wishlist_preview_items = list(wishlist_qs[:3])

    settings_payload = cache.get(SITE_SETTINGS_CACHE_KEY)
    if settings_payload is None:
        settings_obj = SiteSettings.objects.filter(is_active=True).first()
        settings_payload = {
            "site_background_url": settings_obj.background_image.url if settings_obj and settings_obj.background_image else "",
            "site_loader_logo": settings_obj.loader_logo.url if settings_obj and settings_obj.loader_logo else "",
            "sales_offers_label": settings_obj.sales_offers_label if settings_obj and settings_obj.sales_offers_label else "Sales/Offers",
            "sales_offers_enabled": settings_obj.sales_offers_enabled if settings_obj else True,
        }
        cache.set(SITE_SETTINGS_CACHE_KEY, settings_payload, CP_CACHE_TTL)
    site_background_url = settings_payload["site_background_url"]
    # Keep decorative background focused on homepage so content pages remain readable.
    if request.path != "/":
        site_background_url = ""
    site_loader_logo = settings_payload["site_loader_logo"]
    sales_offers_label = settings_payload["sales_offers_label"]
    sales_offers_enabled = settings_payload["sales_offers_enabled"]
    coin_wallet = None
    if request.user.is_authenticated:
        coin_wallet = get_wallet(request.user)

    return {
        'nav_categories': nav_categories,
        'cart_count': cart_count,
        'cart_preview_items': cart_preview_items,
        'cart_preview_total': cart_preview_total,
        'cart_preview_empty': cart_preview_empty,
        'cloudinary_base': cloudinary_base,
        'recently_viewed_books': recently_viewed_books,
        'wishlist_preview_items': wishlist_preview_items,
        'wishlist_count': wishlist_count,
        'site_background_url': site_background_url,
        'site_loader_logo': site_loader_logo,
        'sales_offers_label': sales_offers_label,
        'sales_offers_enabled': sales_offers_enabled,
        'coin_wallet': coin_wallet,
    }
