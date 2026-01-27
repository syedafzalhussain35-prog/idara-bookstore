from django.contrib import admin
from .models import Book, BookImage, Cart, CartItem, Order, OrderItem

# 1. Book Admin (with images)
class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 1

class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'stock')
    inlines = [BookImageInline]

# 2. Order Admin (To see what people bought)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'price', 'quantity')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'city', 'total_cost', 'created_at')
    inlines = [OrderItemInline] # Shows the books inside the order page

# Register everything
admin.site.register(Book, BookAdmin)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)