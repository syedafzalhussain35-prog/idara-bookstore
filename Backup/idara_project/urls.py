from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from store import views


urlpatterns = [

    # ==================================================
    # ADMIN
    # ==================================================
    path('admin/', admin.site.urls),

    # ==================================================
    # DJANGO AUTH (logout, password reset, etc.)
    # ==================================================
    path('accounts/', include('django.contrib.auth.urls')),

    # ==================================================
    # HOME, CATEGORY & SEARCH
    # ==================================================
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.category_books, name='category_books'),
    path('search/', views.search, name='search'),

    # ==================================================
    # STATIC PAGES
    # ==================================================
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('gallery/', views.gallery_view, name='gallery'),

    # ==================================================
    # DOWNLOADS (SYLLABUS PDFs) ✅ FIX
    # ==================================================
    path('downloads/', views.download_list, name='download_list'),

    # ==================================================
    # POLICY PAGES (NAMES FIXED)
    # ==================================================
    path('refund/', views.refund_policy, name='refund_policy'),
    path('shipping/', views.shipping_policy, name='shipping_policy'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_policy, name='terms_policy'),
    path('returns/', views.returns_policy, name='returns_policy'),

    # ==================================================
    # AUTHENTICATION
    # ==================================================
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_page, name='login'),
    path('profile/', views.profile_view, name='profile'),

    # ==================================================
    # BOOK DETAILS
    # ==================================================
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),

    # ==================================================
    # WISHLIST
    # ==================================================
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:book_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('wishlist/add/<int:book_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:book_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # ==================================================
    # CART & CHECKOUT
    # ==================================================
    path('add-to-cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
]


# ==================================================
# MEDIA FILES (DEVELOPMENT ONLY)
# ==================================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
