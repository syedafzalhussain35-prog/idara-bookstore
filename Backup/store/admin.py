from django.contrib import admin
from .models import (
    Book,
    BookImage,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    SyllabusPDF
)

# ======================
# CATEGORY ADMIN
# ======================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)


# ======================
# BOOK IMAGE INLINE
# ======================

class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 1


# ======================
# BOOK ADMIN
# ======================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author',
        'price',
        'mrp_price',
        'discount_display',
        'stock',
        'category',
        'is_bestseller',
        'is_new_arrival',
    )

    list_filter = (
        'category',
        'is_bestseller',
        'is_new_arrival',
    )

    search_fields = ('title', 'author', 'description')
    list_select_related = ('category',)

    list_editable = (
        'price',
        'mrp_price',
        'stock',
        'is_bestseller',
        'is_new_arrival',
    )

    readonly_fields = ('discount_display',)

    inlines = [BookImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'title', 'author', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'mrp_price', 'discount_display')
        }),
        ('Stock', {
            'fields': ('stock',)
        }),
        ('Homepage Flags', {
            'fields': ('is_bestseller', 'is_new_arrival')
        }),
        ('Images', {
            'fields': ('main_cover',)
        }),
    )

    ordering = ('title',)

    @admin.display(description='Discount')
    def discount_display(self, obj):
        if obj.discount_percentage > 0:
            return f"{obj.discount_percentage}% OFF"
        return "—"


# ======================
# ORDER ITEM INLINE
# ======================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'price', 'quantity')
    can_delete = False


# ======================
# ORDER ADMIN
# ======================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'email',
        'total_cost',
        'city',
        'is_paid',
        'created_at',
    )

    list_filter = ('is_paid', 'created_at', 'city')
    search_fields = ('full_name', 'email', 'city', 'user__username')
    readonly_fields = ('user', 'created_at', 'total_cost')

    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    ordering = ('-created_at',)


# ======================
# CART ADMIN
# ======================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]


# ======================
# WISHLIST ADMIN
# ======================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'book__title')
    list_select_related = ('user', 'book')


# ======================
# SYLLABUS PDF ADMIN
# ======================

@admin.register(SyllabusPDF)
class SyllabusPDFAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'semester', 'uploaded_at')
    list_filter = ('category', 'semester')
    search_fields = ('title',)
    ordering = ('category', 'semester')

    fieldsets = (
        ('File Information', {
            'fields': ('title', 'pdf_file')
        }),
        ('Classification', {
            'fields': ('category', 'semester')
        }),
    )
