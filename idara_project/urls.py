from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from store.views import (
    home, book_detail, signup, add_to_cart, cart_detail, 
    checkout, login_page, wishlist_view, profile_view,
    add_to_wishlist, remove_from_wishlist, remove_from_cart,
    contact_view # <--- Add this import
)

urlpatterns = [
    # ... existing paths ...
    path('contact/', contact_view, name='contact'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', home, name='home'),
    path('book/<int:book_id>/', book_detail, name='book_detail'),
    path('signup/', signup, name='signup'),
    path('login/', login_page, name='login'),
    
    # --- WISHLIST & PROFILE ---
    path('wishlist/', wishlist_view, name='wishlist'),
    path('wishlist/add/<int:book_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:book_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('profile/', profile_view, name='profile'),
    # --------------------------

    # --- CART & CHECKOUT ---
    path('add-to-cart/<int:book_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_detail, name='cart_detail'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'), # NEW PATH
    path('checkout/', checkout, name='checkout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)