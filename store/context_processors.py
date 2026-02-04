from .models import Category, Cart
from django.db.models import Sum

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

    # 2. Fetch Cart Count
    cart_count = 0
    if request.user.is_authenticated:
        # Get the cart for the logged-in user
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            # Aggregate the sum of all item quantities in the cart
            result = cart.items.aggregate(total_qty=Sum('quantity'))
            cart_count = result.get('total_qty') or 0
    else:
        # For guest users, check if a cart_id exists in the session
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
            if cart:
                result = cart.items.aggregate(total_qty=Sum('quantity'))
                cart_count = result.get('total_qty') or 0

    return {
        'nav_categories': nav_categories,
        'cart_count': cart_count,
    }