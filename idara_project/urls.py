from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Add 'checkout' to the list below
from store.views import home, book_detail, signup, add_to_cart, cart_detail, checkout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', home, name='home'),
    path('book/<int:book_id>/', book_detail, name='book_detail'),
    path('signup/', signup, name='signup'),
    
    path('add-to-cart/<int:book_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_detail, name='cart_detail'),
    
    # NEW LINE HERE:
    path('checkout/', checkout, name='checkout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)