from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from django.contrib import messages
from django.urls import path
from django.shortcuts import render
from django.db import transaction
from decimal import Decimal, InvalidOperation
import re
from django.contrib.admin.helpers import ActionForm
from django.http import HttpResponse
import csv

from .models import (
    Book,
    BookImage,
    Cart,
    CartItem,
    CartBundleItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    Subject,
    SyllabusPDF,
    Review,
    Coupon,
    GalleryItem,
    UserProfile,
    UserAddress,
    Bundle,
    PublishWithUsSubmission,
    Banner,
    SearchQueryLog,
    AuditLog,
    SiteSettings,
)
from .admin_site import IdaraAdminSite

admin_site = IdaraAdminSite(name="idara_admin")

def _log_audit(request, action, obj, changes):
    AuditLog.objects.create(
        user=request.user if request and request.user.is_authenticated else None,
        action=action,
        model_name=obj.__class__.__name__,
        object_id=obj.pk or 0,
        object_repr=str(obj)[:200],
        changes=changes,
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


class BundleBookInline(admin.TabularInline):
    model = Bundle.books.through
    extra = 1


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "bundle_price", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name",)
    inlines = [BundleBookInline]
    exclude = ("books",)


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
        "is_trending",
        "is_new_arrival",
        "is_featured",
    )

    list_filter = (
        "category",
        ("subjects", admin.RelatedOnlyFieldListFilter),
        "is_bestseller",
        "is_trending",
        "is_new_arrival",
        "is_featured",
    )
    search_fields = ("title", "author", "description")
    list_select_related = ("category",)

    list_editable = (
        "price",
        "mrp_price",
        "stock",
        "is_bestseller",
        "is_trending",
        "is_new_arrival",
        "is_featured",
    )

    readonly_fields = ("discount_display",)
    inlines = [BookImageInline]

    change_list_template = "admin/store/book/change_list.html"

    fieldsets = (
        ("Basic Information", {
            "fields": ("category", "subjects", "title", "author", "description")
        }),
        ("Specifications", {
            "fields": ("isbn", "published_year", "binding", "pages", "weight", "readership")
        }),
        ("Pricing", {
            "fields": ("price", "mrp_price", "discount_display")
        }),
        ("Stock", {
            "fields": ("stock",)
        }),
        ("Homepage Flags", {
            "fields": ("is_bestseller", "is_trending", "is_new_arrival", "is_featured")
        }),
        ("Images", {
            "fields": ("main_cover",)
        }),
        ("Book Files", {
            "fields": ("toc_pdf", "sample_pdf")
        }),
    )

    ordering = ("title",)

    class PriceUpdateActionForm(ActionForm):
        percentage = forms.DecimalField(
            required=False,
            label="Price %",
            help_text="Use positive or negative (e.g., 10 or -5).",
        )
        apply_to_mrp = forms.BooleanField(
            required=False,
            initial=True,
            label="Apply to MRP too",
        )

    action_form = PriceUpdateActionForm
    actions = ("bulk_update_price", "export_books_csv")

    class ImportBooksForm(forms.Form):
        file = forms.FileField(help_text="Upload XLSX file.")
        dry_run = forms.BooleanField(required=False, initial=False, help_text="Validate only.")

    class ImportImagesForm(forms.Form):
        root_path = forms.CharField(
            help_text="Server path containing folders named 'Title (Author)'."
        )
        replace_existing = forms.BooleanField(
            required=False,
            initial=False,
            help_text="Replace existing images for matched books.",
        )
        dry_run = forms.BooleanField(required=False, initial=False, help_text="Validate only.")

    def save_model(self, request, obj, form, change):
        original = None
        if change and obj.pk:
            original = Book.objects.filter(pk=obj.pk).first()

        super().save_model(request, obj, form, change)

        if not original:
            return

        if original.price != obj.price:
            _log_audit(
                request,
                "book_price_change",
                obj,
                {"price": {"from": str(original.price), "to": str(obj.price)}},
            )
        if original.stock != obj.stock:
            _log_audit(
                request,
                "book_stock_change",
                obj,
                {"stock": {"from": original.stock, "to": obj.stock}},
            )

    @admin.display(description="Discount")
    def discount_display(self, obj):
        if obj.discount_percentage > 0:
            return f"{obj.discount_percentage}% OFF"
        return "—"



    @admin.action(description="Bulk update price by percent")
    def bulk_update_price(self, request, queryset):
        raw = request.POST.get("percentage")
        if raw in (None, ""):
            self.message_user(request, "Enter a percentage value.", level="error")
            return
        try:
            pct = Decimal(str(raw))
        except Exception:
            self.message_user(request, "Invalid percentage.", level="error")
            return

        apply_to_mrp = bool(request.POST.get("apply_to_mrp"))
        factor = (Decimal("100") + pct) / Decimal("100")
        updated = 0

        for book in queryset:
            original_price = book.price
            book.price = (book.price * factor).quantize(Decimal("0.01"))
            if apply_to_mrp and book.mrp_price:
                book.mrp_price = (book.mrp_price * factor).quantize(Decimal("0.01"))
            book.save(update_fields=["price", "mrp_price"])
            if original_price != book.price:
                _log_audit(
                    request,
                    "book_price_change",
                    book,
                    {"price": {"from": str(original_price), "to": str(book.price)}},
                )
            updated += 1

        self.message_user(request, f"Updated {updated} books.")

    @admin.action(description="Export selected books to CSV")
    def export_books_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="books.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Title", "Author", "Category", "Price", "MRP", "Stock"])
        for book in queryset:
            writer.writerow([
                book.id,
                book.title,
                book.author,
                book.category.name if book.category else "",
                book.price,
                book.mrp_price or "",
                book.stock,
            ])
        return response

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-books/",
                self.admin_site.admin_view(self.import_books_view),
                name="store_book_import_books",
            ),
            path(
                "import-images/",
                self.admin_site.admin_view(self.import_images_view),
                name="store_book_import_images",
            ),
        ]
        return custom_urls + urls

    def _normalize_header(self, val):
        return str(val or "").strip().lower()

    def _split_subjects(self, raw):
        if not raw:
            return []
        parts = re.split(r"[\/,|]+", str(raw))
        return [p.strip() for p in parts if p.strip()]

    def import_books_view(self, request):
        form = self.ImportBooksForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                from openpyxl import load_workbook
            except Exception:
                messages.error(request, "openpyxl is not installed. Add it to requirements and deploy.")
                return render(request, "admin/store/book/import_books.html", {"form": form})

            file = form.cleaned_data["file"]
            dry_run = form.cleaned_data["dry_run"]

            wb = load_workbook(file, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                messages.error(request, "The file appears to be empty.")
                return render(request, "admin/store/book/import_books.html", {"form": form})

            headers = [self._normalize_header(h) for h in rows[0]]
            header_map = {h: idx for idx, h in enumerate(headers)}

            def get_val(row, key):
                idx = header_map.get(key)
                return row[idx] if idx is not None else None

            created = 0
            updated = 0
            errors = 0

            with transaction.atomic():
                for row in rows[1:]:
                    title = (get_val(row, "book title") or get_val(row, "title") or "").strip()
                    author = (get_val(row, "author") or "").strip()
                    if not title or not author:
                        errors += 1
                        continue

                    category_name = (get_val(row, "category") or "").strip()
                    subject_raw = get_val(row, "subject") or get_val(row, "subjects")
                    isbn = (get_val(row, "isbn") or "").strip()
                    price_raw = get_val(row, "rate") or get_val(row, "price")

                    book, is_created = Book.objects.get_or_create(
                        title=title,
                        author=author,
                        defaults={"isbn": isbn or "", "price": Decimal("0.00")},
                    )

                    if category_name:
                        category, _ = Category.objects.get_or_create(name=category_name)
                        book.category = category

                    if isbn:
                        book.isbn = isbn

                    if price_raw not in (None, ""):
                        try:
                            book.price = Decimal(str(price_raw))
                        except (InvalidOperation, ValueError):
                            pass

                    if not dry_run:
                        book.save()

                    subjects = self._split_subjects(subject_raw)
                    if subjects and not dry_run:
                        subject_objs = []
                        for s in subjects:
                            obj, _ = Subject.objects.get_or_create(name=s)
                            subject_objs.append(obj)
                        book.subjects.set(subject_objs)

                    if is_created:
                        created += 1
                    else:
                        updated += 1

                if dry_run:
                    transaction.set_rollback(True)

            messages.success(
                request,
                f"Import completed. Created: {created}, Updated: {updated}, Errors: {errors}"
                + (" (dry run)" if dry_run else ""),
            )

        return render(request, "admin/store/book/import_books.html", {"form": form})

    def import_images_view(self, request):
        form = self.ImportImagesForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            root_path = form.cleaned_data["root_path"].strip()
            replace_existing = form.cleaned_data["replace_existing"]
            dry_run = form.cleaned_data["dry_run"]

            from pathlib import Path
            from django.core.files import File

            root = Path(root_path)
            if not root.exists() or not root.is_dir():
                messages.error(request, "Root path does not exist or is not a directory.")
                return render(request, "admin/store/book/import_images.html", {"form": form})

            created = 0
            skipped = 0
            errors = 0

            with transaction.atomic():
                for folder in root.iterdir():
                    if not folder.is_dir():
                        continue
                    match = re.match(r"^(.*)\((.*)\)$", folder.name)
                    if not match:
                        skipped += 1
                        continue
                    title = match.group(1).strip()
                    author = match.group(2).strip()
                    if not title or not author:
                        skipped += 1
                        continue

                    book = Book.objects.filter(title=title, author=author).first()
                    if not book:
                        skipped += 1
                        continue

                    if replace_existing and not dry_run:
                        if book.main_cover:
                            book.main_cover.delete(save=False)
                        book.images.all().delete()

                    image_files = sorted(
                        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}],
                        key=lambda p: p.stem,
                    )

                    if not image_files:
                        skipped += 1
                        continue

                    if not dry_run:
                        # 1.jpg as main cover
                        main = image_files[0]
                        with main.open("rb") as fh:
                            book.main_cover.save(main.name, File(fh), save=True)

                        for extra in image_files[1:]:
                            with extra.open("rb") as fh:
                                BookImage.objects.create(book=book, image=File(fh, name=extra.name))

                    created += 1

                if dry_run:
                    transaction.set_rollback(True)

            messages.success(
                request,
                f"Image import completed. Updated: {created}, Skipped: {skipped}, Errors: {errors}"
                + (" (dry run)" if dry_run else ""),
            )

        return render(request, "admin/store/book/import_images.html", {"form": form})
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
        "status",
        "is_paid",
        "created_at",
    )

    list_filter = ("status", "is_paid", "created_at", "city")
    search_fields = ("full_name", "email", "city", "user__username")
    readonly_fields = (
        "user",
        "created_at",
        "subtotal",
        "discount_amount",
        "gst_rate",
        "gst_amount",
        "shipping_amount",
        "total_cost",
    )

    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    ordering = ("-created_at",)
    actions = ("export_orders_csv",)

    def save_model(self, request, obj, form, change):
        original = None
        if change and obj.pk:
            original = Order.objects.filter(pk=obj.pk).first()

        super().save_model(request, obj, form, change)

        if not original:
            return

        if original.is_paid != obj.is_paid:
            _log_audit(
                request,
                "order_paid_change",
                obj,
                {"is_paid": {"from": original.is_paid, "to": obj.is_paid}},
            )
        if original.status != obj.status:
            _log_audit(
                request,
                "order_status_change",
                obj,
                {"status": {"from": original.status, "to": obj.status}},
            )

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



    @admin.action(description="Export selected orders to CSV")
    def export_orders_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="orders.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "ID",
            "Name",
            "Email",
            "City",
            "Total",
            "Paid",
            "Created",
        ])
        for order in queryset:
            writer.writerow([
                order.id,
                order.full_name,
                order.email,
                order.city,
                order.total_cost,
                "Yes" if order.is_paid else "No",
                order.created_at,
            ])
        return response
# ======================
# CART ADMIN
# ======================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class CartBundleItemInline(admin.TabularInline):
    model = CartBundleItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username",)
    inlines = [CartItemInline, CartBundleItemInline]


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


# ======================
# USER PROFILE ADMIN
# ======================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "company", "updated_at")
    search_fields = ("user__username", "user__email", "phone", "city", "company")
    ordering = ("-updated_at",)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "zip_code", "is_default", "created_at")
    list_filter = ("is_default", "city")
    search_fields = ("user__username", "user__email", "label", "address", "city", "zip_code")
    ordering = ("-created_at",)


@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ("query", "results_count", "user", "created_at")
    list_filter = ("results_count", "created_at")
    search_fields = ("query", "category_slug", "subject_slug", "ip_address")
    ordering = ("-created_at",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "model_name", "object_id", "user", "created_at")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("object_repr", "user__username", "user__email")
    readonly_fields = ("user", "action", "model_name", "object_id", "object_repr", "changes", "created_at")
    ordering = ("-created_at",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    ordering = ("-created_at",)
    fieldsets = (
        ("Branding", {
            "fields": ("background_image", "loader_logo")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PublishWithUsSubmission)
class PublishWithUsSubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "author_name", "email", "phone", "created_at")
    search_fields = ("title", "author_name", "email", "phone")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "title",
        "category",
        "order",
        "is_active",
        "focal_x",
        "focal_y",
        "mobile_height",
        "tablet_height",
    )
    list_editable = ("order", "is_active", "focal_x", "focal_y", "mobile_height", "tablet_height")
    search_fields = ("title", "headline", "subheadline")
    ordering = ("order", "id")

    fieldsets = (
        ("Banner", {
            "fields": ("title", "headline", "subheadline", "image", "category", "order", "is_active")
        }),
        ("CTA", {
            "fields": ("cta_text", "cta_category")
        }),
        ("Mobile & Crop", {
            "fields": ("focal_x", "focal_y", "mobile_height", "tablet_height")
        }),
    )

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px;width:86px;object-fit:cover;border-radius:6px;border:1px solid #243149;" />',
                obj.image.url,
            )
        return "?"

# ======================
# CUSTOM ADMIN SITE
# ======================

admin_site.register(Category, CategoryAdmin)
admin_site.register(Book, BookAdmin)
admin_site.register(Bundle, BundleAdmin)
admin_site.register(Subject, SubjectAdmin)
admin_site.register(Cart, CartAdmin)
admin_site.register(Wishlist, WishlistAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(Coupon, CouponAdmin)
admin_site.register(SyllabusPDF, SyllabusPDFAdmin)
admin_site.register(GalleryItem, GalleryItemAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(UserAddress, UserAddressAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(PublishWithUsSubmission, PublishWithUsSubmissionAdmin)
admin_site.register(Banner, BannerAdmin)
admin_site.register(SearchQueryLog, SearchQueryLogAdmin)
admin_site.register(AuditLog, AuditLogAdmin)
