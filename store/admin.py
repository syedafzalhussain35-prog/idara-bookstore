from django.contrib import admin
from .models import Book, BookImage, Cart, CartItem, Order, OrderItem, Wishlist, Category

# 1. Category Admin (NEW)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)} # Auto-fills slug when you type name

# 2. Book Gallery Inline
class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 1 

# 3. Book Admin Configuration
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'stock', 'category') # Added category here
    search_fields = ('title', 'author')
    list_filter = ('category', 'author') # Added category filter here
    inlines = [BookImageInline] 

# 4. Order Item Inline
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'price', 'quantity')
    can_delete = False

# 5. Order Admin Configuration
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'total_cost', 'city', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'created_at')
    search_fields = ('full_name', 'address', 'city', 'user__username')
    inlines = [OrderItemInline]
    readonly_fields = ('user', 'created_at', 'total_cost')

# 6. Cart Admin
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    inlines = [CartItemInline]

# Register models
admin.site.register(Book, BookAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Wishlist)