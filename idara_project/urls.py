from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store import views
from store.admin import admin_site

urlpatterns = [

    # ==================================================
    # ADMIN
    # ==================================================
    path('admin/', admin_site.urls),

    # ==================================================
    # AUTH (DJANGO-ALLAUTH)
    # ==================================================
    path('accounts/', include('allauth.urls')),

    # ==================================================
    # HOME & CATEGORY
    # ==================================================
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.category_books, name='category_books'),

    # ==================================================
    # SEARCH
    # ==================================================
    path('search/', views.search, name='search'),
    path('search/live/', views.live_search, name='live_search'),

    # ==================================================
    # STATIC PAGES
    # ==================================================
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('gallery/', views.gallery_view, name='gallery'),

    # ==================================================
    # POLICY PAGES
    # ==================================================
    path('refund/', views.refund_policy, name='refund_policy'),
    path('shipping/', views.shipping_policy, name='shipping_policy'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_policy, name='terms_policy'),
    path('returns/', views.returns_policy, name='returns_policy'),
    path('publish-with-us/', views.publish_with_us, name='publish_with_us'),

    # ==================================================
    # USER
    # ==================================================
    path('profile/', views.profile_view, name='profile'),

    # ==================================================
    # BOOKS & REVIEWS
    # ==================================================
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/<int:book_id>/review/', views.add_review, name='add_review'),

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
# STATIC & MEDIA (DEV ONLY)
# ==================================================
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
