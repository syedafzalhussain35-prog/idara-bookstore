from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from store.views import (
    home,
    book_detail,
    signup,
    login_page,
    add_to_cart,
    cart_detail,
    remove_from_cart,
    checkout,
    wishlist_view,
    add_to_wishlist,
    remove_from_wishlist,
    profile_view,
    contact_view,
    about_view,
    gallery_view,

    # ✅ POLICY VIEWS
    refund_policy,
    shipping_policy,
    privacy_policy,
    terms_policy,
    returns_policy,
)

urlpatterns = [

    # ==================================================
    # ADMIN
    # ==================================================
    path('admin/', admin.site.urls),

    # ==================================================
    # DJANGO AUTH
    # ==================================================
    path('accounts/', include('django.contrib.auth.urls')),

    # ==================================================
    # STATIC PAGES
    # ==================================================
    path('', home, name='home'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('gallery/', gallery_view, name='gallery'),

    # ==================================================
    # POLICY PAGES ✅
    # ==================================================
    path('refund/', refund_policy, name='refund'),
    path('shipping/', shipping_policy, name='shipping'),
    path('privacy/', privacy_policy, name='privacy'),
    path('terms/', terms_policy, name='terms'),
    path('returns/', returns_policy, name='returns'),

    # ==================================================
    # AUTHENTICATION
    # ==================================================
    path('signup/', signup, name='signup'),
    path('login/', login_page, name='login'),

    # ==================================================
    # BOOKS
    # ==================================================
    path('book/<int:book_id>/', book_detail, name='book_detail'),

    # ==================================================
    # WISHLIST & PROFILE
    # ==================================================
    path('wishlist/', wishlist_view, name='wishlist'),
    path('wishlist/add/<int:book_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:book_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('profile/', profile_view, name='profile'),

    # ==================================================
    # CART & CHECKOUT
    # ==================================================
    path('add-to-cart/<int:book_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_detail, name='cart_detail'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('checkout/', checkout, name='checkout'),
]

# ==================================================
# MEDIA FILES (DEV ONLY)
# ==================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
