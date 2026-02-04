from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Book,
    BookImage,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    SyllabusPDF,
    Review,
    Coupon,
    GalleryItem,
)

# ======================
# CATEGORY ADMIN
# ======================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    ordering = ("name",)


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
        "title",
        "author",
        "price",
        "mrp_price",
        "discount_display",
        "stock",
        "category",
        "is_bestseller",
        "is_new_arrival",
    )

    list_filter = ("category", "is_bestseller", "is_new_arrival")
    search_fields = ("title", "author", "description")
    list_select_related = ("category",)

    list_editable = (
        "price",
        "mrp_price",
        "stock",
        "is_bestseller",
        "is_new_arrival",
    )

    readonly_fields = ("discount_display",)
    inlines = [BookImageInline]

    fieldsets = (
        ("Basic Information", {
            "fields": ("category", "title", "author", "description")
        }),
        ("Pricing", {
            "fields": ("price", "mrp_price", "discount_display")
        }),
        ("Stock", {
            "fields": ("stock",)
        }),
        ("Homepage Flags", {
            "fields": ("is_bestseller", "is_new_arrival")
        }),
        ("Images", {
            "fields": ("main_cover",)
        }),
    )

    ordering = ("title",)

    @admin.display(description="Discount")
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
    readonly_fields = ("book", "price", "quantity")
    can_delete = False


# ======================
# ORDER ADMIN (GUEST-SAFE)
# ======================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email_link",
        "total_cost_display",
        "city",
        "is_paid",
        "created_at",
    )

    list_filter = ("is_paid", "created_at", "city")
    search_fields = ("full_name", "email", "city", "user__username")
    readonly_fields = ("user", "created_at", "total_cost")

    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    ordering = ("-created_at",)

    @admin.display(description="Email")
    def email_link(self, obj):
        return format_html(
            '<a href="mailto:{}">{}</a>',
            obj.email,
            obj.email
        )

    @admin.display(description="Total Cost")
    def total_cost_display(self, obj):
        return f"₹{obj.total_cost}"


# ======================
# CART ADMIN
# ======================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username",)
    inlines = [CartItemInline]


# ======================
# WISHLIST ADMIN
# ======================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "created_at")
    search_fields = ("user__username", "book__title")
    list_select_related = ("user", "book")


# ======================
# REVIEW ADMIN
# ======================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "book",
        "user",
        "rating",
        "short_comment",
        "created_at",
    )

    list_filter = ("rating", "created_at")
    search_fields = ("book__title", "user__username", "comment")
    list_select_related = ("book", "user")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    @admin.display(description="Comment")
    def short_comment(self, obj):
        return (obj.comment[:50] + "…") if obj.comment else "—"


# ======================
# COUPON ADMIN
# ======================

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "value",
        "active",
        "expiry_date",
        "is_valid_coupon",
        "created_at",
    )

    list_filter = ("discount_type", "active")
    search_fields = ("code",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Coupon Details", {
            "fields": ("code", "discount_type", "value")
        }),
        ("Status & Expiry", {
            "fields": ("expiry_date", "active")
        }),
    )

    readonly_fields = ("created_at",)

    @admin.display(boolean=True, description="Valid")
    def is_valid_coupon(self, obj):
        if not obj.active:
            return False
        if obj.expiry_date and obj.expiry_date < timezone.now().date():
            return False
        return True

    def save_model(self, request, obj, form, change):
        if obj.expiry_date and obj.expiry_date < timezone.now().date():
            obj.active = False
        super().save_model(request, obj, form, change)


# ======================
# SYLLABUS PDF ADMIN
# ======================

@admin.register(SyllabusPDF)
class SyllabusPDFAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "semester", "uploaded_at")
    list_filter = ("category", "semester")
    search_fields = ("title",)
    ordering = ("category", "semester")

    fieldsets = (
        ("File Information", {
            "fields": ("title", "pdf_file")
        }),
        ("Classification", {
            "fields": ("category", "semester")
        }),
    )


# ======================
# GALLERY ADMIN
# ======================

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("event", "media_type", "title", "order", "created_at")
    list_filter = ("event", "media_type")
    search_fields = ("event", "title", "media")
    ordering = ("event", "order", "created_at")
    readonly_fields = ("created_at",)
