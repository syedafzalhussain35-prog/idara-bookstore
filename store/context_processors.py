from .models import Category, Cart, Book, Wishlist, SiteSettings
from django.db.models import Sum, Case, When, IntegerField
from django.conf import settings

def navbar_categories(request):
    """
    Exposes categories and cart count globally to all templates.
    """
    # 1. Fetch Categories for the dropdown
    nav_categories = (
        Category.objects
        .only('name', 'slug')
        .all()
        .order_by('name')
    )

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

    settings_obj = SiteSettings.objects.filter(is_active=True).first()
    site_background_url = settings_obj.background_image.url if settings_obj and settings_obj.background_image else ""
    site_loader_logo = settings_obj.loader_logo.url if settings_obj and settings_obj.loader_logo else ""

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
    }
