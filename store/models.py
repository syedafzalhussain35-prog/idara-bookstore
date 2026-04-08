from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, F, Avg
from django.conf import settings
from decimal import Decimal
import os
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit
from django.core.files.base import ContentFile

from .dictionary_text import (
    normalize_latin_search_text,
    normalize_script_text,
    normalize_transliteration_text,
)

# ======================
# CATEGORY
# ======================

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            max_len = self._meta.get_field("slug").max_length or 50
            base_slug = (slugify(self.name) or "category")[:max_len]
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                suffix = f"-{counter}"
                slug = f"{base_slug[:max_len - len(suffix)]}{suffix}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ======================
# BOOKS
# ======================

class Book(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )

    title = models.CharField(max_length=200, db_index=True)
    author = models.CharField(max_length=200, db_index=True)
    system_id = models.CharField(max_length=80, blank=True, null=True, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True)
    published_year = models.CharField(max_length=10, blank=True)
    binding = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=20, blank=True)
    weight = models.CharField(max_length=20, blank=True)
    subjects = models.ManyToManyField("Subject", blank=True, related_name="books")

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    mrp_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    stock = models.PositiveIntegerField(default=0)

    main_cover = models.ImageField(
        upload_to='books/covers/',
        blank=True,
        null=True
    )

    toc_pdf = models.FileField(upload_to='books/pdfs/', blank=True, null=True)
    sample_pdf = models.FileField(upload_to='books/pdfs/', blank=True, null=True)

    is_bestseller = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    is_watermarked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
            models.Index(fields=['price']),
        ]

    @property
    def discount_percentage(self):
        if self.mrp_price and self.mrp_price > self.price:
            return round(((self.mrp_price - self.price) / self.mrp_price) * 100)
        return 0

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def average_rating(self):
        return round(self.reviews.aggregate(avg=Avg('rating'))['avg'] or 0, 1)

    def __str__(self):
        return self.title

    def _apply_watermark_if_needed(self):
        if not self.main_cover or self.is_watermarked:
            return
        if not getattr(settings, "BOOK_WATERMARK_ENABLED", True):
            return
        text = getattr(settings, "BOOK_WATERMARK_TEXT", "Idara")
        if _apply_text_watermark(self.main_cover, text):
            self.is_watermarked = True
            super().save(update_fields=["main_cover", "is_watermarked"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._apply_watermark_if_needed()

    def _cloudinary_file_url(self, url):
        if not url:
            return ""
        raw = str(url).strip()
        clean = raw

        # Extract first URL-like token and trim accidental trailing paste chars.
        if "http://" in raw or "https://" in raw:
            for token in raw.split():
                if token.startswith("http://") or token.startswith("https://"):
                    clean = token
                    break
        clean = clean.strip("[]()'\",")
        if clean.startswith("http://"):
            clean = "https://" + clean[len("http://"):]

        # Strip query/hash noise if accidentally persisted with the URL.
        parts = urlsplit(clean)
        clean = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

        return clean

    @property
    def toc_pdf_url(self):
        if not self.toc_pdf:
            return ""
        return self._cloudinary_file_url(self.toc_pdf.url)

    @property
    def sample_pdf_url(self):
        if not self.sample_pdf:
            return ""
        return self._cloudinary_file_url(self.sample_pdf.url)


class BookImage(models.Model):
    book = models.ForeignKey(
        Book,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='books/gallery/')
    is_watermarked = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.book.title}"

    def _apply_watermark_if_needed(self):
        if not self.image or self.is_watermarked:
            return
        if not getattr(settings, "BOOK_WATERMARK_ENABLED", True):
            return
        text = getattr(settings, "BOOK_WATERMARK_TEXT", "Idara")
        if _apply_text_watermark(self.image, text):
            self.is_watermarked = True
            super().save(update_fields=["image", "is_watermarked"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._apply_watermark_if_needed()


# ======================
# SUBJECTS
# ======================

class Subject(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    icon = models.ImageField(upload_to='subjects/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            max_len = self._meta.get_field("slug").max_length or 50
            base_slug = (slugify(self.name) or "subject")[:max_len]
            slug = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug).exists():
                suffix = f"-{counter}"
                slug = f"{base_slug[:max_len - len(suffix)]}{suffix}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ======================
# BANNERS
# ======================

class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    subheadline = models.CharField(max_length=300, blank=True)
    cta_text = models.CharField(max_length=50, blank=True)
    cta_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="banner_ctas",
    )
    image = models.ImageField(upload_to='banners/')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="banners",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    show_on_mobile = models.BooleanField(
        default=True,
        help_text="Enable this banner for mobile screens.",
    )
    show_on_desktop = models.BooleanField(
        default=True,
        help_text="Enable this banner for desktop/tablet screens.",
    )
    focal_x = models.PositiveSmallIntegerField(default=50)
    focal_y = models.PositiveSmallIntegerField(default=50)
    desktop_crop_x = models.PositiveIntegerField(default=0)
    desktop_crop_y = models.PositiveIntegerField(default=0)
    desktop_crop_width = models.PositiveIntegerField(default=0)
    desktop_crop_height = models.PositiveIntegerField(default=0)
    mobile_crop_x = models.PositiveIntegerField(default=0)
    mobile_crop_y = models.PositiveIntegerField(default=0)
    mobile_crop_width = models.PositiveIntegerField(default=0)
    mobile_crop_height = models.PositiveIntegerField(default=0)
    mobile_height = models.PositiveSmallIntegerField(
        default=360,
        help_text="Banner height in pixels for mobile screens.",
    )
    tablet_height = models.PositiveSmallIntegerField(
        default=420,
        help_text="Banner height in pixels for tablet screens.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title or f"Banner {self.id}"

    @property
    def webp_name(self):
        if not self.image:
            return ""
        base, _ = os.path.splitext(self.image.name)
        return f"{base}.webp"

    def _crop_variant_name(self, variant):
        if not self.image:
            return ""
        base, _ = os.path.splitext(self.image.name)
        return f"{base}__{variant}.webp"

    def has_webp(self):
        if not self.image:
            return False
        try:
            return self.image.storage.exists(self.webp_name)
        except Exception:
            return False

    def webp_url(self):
        if self.has_webp():
            return self.image.storage.url(self.webp_name)
        return self.image.url if self.image else ""

    def _crop_variant_url(self, variant):
        name = self._crop_variant_name(variant)
        if not name:
            return ""
        try:
            if self.image.storage.exists(name):
                return self.image.storage.url(name)
        except Exception:
            return ""
        return ""

    @property
    def desktop_crop_url(self):
        return self._crop_variant_url("desktop")

    @property
    def mobile_crop_url(self):
        return self._crop_variant_url("mobile")

    def _ensure_webp(self):
        if not self.image:
            return
        if self.image.name.lower().endswith(".webp"):
            return
        if self.has_webp():
            return
        try:
            from PIL import Image
        except Exception:
            return
        try:
            # Some remote storages (e.g. Cloudinary) may not allow reopening an
            # already-saved file object in admin edits. Skip conversion instead
            # of breaking the save request.
            self.image.open()
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="WEBP", quality=82, method=6)
            buffer.seek(0)
            self.image.storage.save(self.webp_name, ContentFile(buffer.read()))
        except Exception:
            return

    def _safe_crop_box(self, img_width, img_height, x, y, w, h):
        if w <= 0 or h <= 0:
            return (0, 0, img_width, img_height)

        x = max(0, min(x, img_width - 1))
        y = max(0, min(y, img_height - 1))
        w = max(1, min(w, img_width - x))
        h = max(1, min(h, img_height - y))
        return (x, y, x + w, y + h)

    def _ensure_cropped_variants(self):
        if not self.image:
            return

        try:
            from PIL import Image
        except Exception:
            return

        try:
            self.image.open()
            img = Image.open(self.image)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            elif img.mode == "RGBA":
                img = img.convert("RGB")
        except Exception:
            return

        crop_specs = {
            "desktop": (
                int(self.desktop_crop_x or 0),
                int(self.desktop_crop_y or 0),
                int(self.desktop_crop_width or 0),
                int(self.desktop_crop_height or 0),
            ),
            "mobile": (
                int(self.mobile_crop_x or 0),
                int(self.mobile_crop_y or 0),
                int(self.mobile_crop_width or 0),
                int(self.mobile_crop_height or 0),
            ),
        }

        for variant, (x, y, w, h) in crop_specs.items():
            try:
                box = self._safe_crop_box(img.width, img.height, x, y, w, h)
                cropped = img.crop(box)
                buffer = BytesIO()
                cropped.save(buffer, format="WEBP", quality=82, method=6)
                buffer.seek(0)
                name = self._crop_variant_name(variant)
                try:
                    if self.image.storage.exists(name):
                        self.image.storage.delete(name)
                except Exception:
                    pass
                self.image.storage.save(name, ContentFile(buffer.read()))
            except Exception:
                continue

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._ensure_webp()
        self._ensure_cropped_variants()
        # Keep homepage banner lists fresh after admin updates/uploads.
        from django.core.cache import cache
        cache.delete_many([
            "home:banners:mobile",
            "home:banners:mobile:fallback",
            "home:banners:desktop",
        ])

# ======================
# BUNDLES
# ======================

class Bundle(models.Model):
    name = models.CharField(max_length=200)
    books = models.ManyToManyField(Book, related_name='bundles')
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def original_total(self):
        total = self.books.aggregate(total=Sum('price'))['total']
        return total or Decimal('0.00')


# ======================
# PUBLISH WITH US SUBMISSIONS
# ======================

class PublishWithUsSubmission(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    author_name = models.CharField(max_length=200)
    position_affiliation = models.CharField(max_length=200, blank=True)
    mailing_address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    topic_definition = models.TextField(blank=True)
    overview = models.TextField(blank=True)
    reasons = models.TextField(blank=True)
    unique_features = models.TextField(blank=True)
    competition = models.TextField(blank=True)
    toc = models.TextField(blank=True)
    pages = models.CharField(max_length=50, blank=True)
    delivery_time = models.CharField(max_length=100, blank=True)
    text_electronic = models.CharField(max_length=20, blank=True)
    text_software = models.CharField(max_length=200, blank=True)
    special_features = models.TextField(blank=True)
    figures_computer = models.CharField(max_length=20, blank=True)
    figures_software = models.CharField(max_length=200, blank=True)
    market = models.TextField(blank=True)
    societies = models.TextField(blank=True)
    journals = models.TextField(blank=True)
    textbook_details = models.TextField(blank=True)
    previous_works = models.TextField(blank=True)
    why_better = models.TextField(blank=True)
    reviewers = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.author_name}"


# ======================
# USER PROFILE
# ======================

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    company = models.CharField(max_length=200, blank=True)
    iks_follow_instagram = models.BooleanField(default=False)
    iks_follow_facebook = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=100, default="Home")
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label} - {self.address[:30]}"


# ======================
# GALLERY (EVENT MEDIA)
# ======================

class GalleryItem(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    event = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    media = models.FileField(upload_to='gallery/')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event', 'order', 'id']

    def __str__(self):
        label = self.title or self.media.name
        return f"{self.event} - {label}"


# ======================
# REVIEWS & RATINGS ⭐⭐⭐⭐⭐
# ======================

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(
        Book,
        related_name='reviews',
        on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.book.title} - {self.rating}★"


# ======================
# CART
# ======================

class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart ({self.user})"

    def get_total(self):
        total = self.items.aggregate(
            total=Sum(F('quantity') * F('book__price'))
        )['total']
        bundle_total = self.bundle_items.aggregate(
            total=Sum(F('quantity') * F('bundle__bundle_price'))
        )['total']
        return (total or Decimal('0.00')) + (bundle_total or Decimal('0.00'))


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'book')

    @property
    def total_price(self):
        return self.quantity * self.book.price

    def __str__(self):
        return f"{self.book.title} × {self.quantity}"


# ======================
# CART BUNDLES
# ======================

class CartBundleItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name='bundle_items',
        on_delete=models.CASCADE
    )
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'bundle')

    @property
    def total_price(self):
        return self.quantity * self.bundle.bundle_price

    def __str__(self):
        return f"{self.bundle.name} × {self.quantity}"


# COUPONS & PROMOTIONS 🎟️
# ======================

from django.utils import timezone


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('flat', 'Flat Amount'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage or flat amount"
    )
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valid_categories = models.ManyToManyField("Category", blank=True, related_name="coupons")
    active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    # ✅ CHECK IF COUPON IS VALID
    def is_valid(self):
        if not self.active:
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        return True

    # ✅ AUTO-DISABLE EXPIRED COUPONS
    def save(self, *args, **kwargs):
        if self.expiry_date and self.expiry_date < timezone.now().date():
            self.active = False
        super().save(*args, **kwargs)

    def validate_for_cart(self, *, subtotal, category_ids):
        if not self.active:
            return False, "❌ Coupon inactive."
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False, "❌ Coupon expired."
        if subtotal < self.minimum_order_amount:
            return False, f"❌ Minimum order ₹{self.minimum_order_amount} required."
        valid_ids = set(self.valid_categories.values_list("id", flat=True))
        if valid_ids and not (set(category_ids) & valid_ids):
            return False, "❌ Not valid for this category."
        return True, "Coupon applied."

    def discount_amount_for_subtotal(self, subtotal):
        if self.discount_type == "percent":
            return (subtotal * self.value) / Decimal("100")
        return min(self.value, subtotal)
# ======================
# ORDERS
# ======================
# ======================
# ORDERS
# ======================

class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    # Recommended: Add a status field to track shipping progress
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    sub_status = models.CharField(max_length=80, blank=True, default="")
    customer_note = models.TextField(blank=True, default="")
    internal_comment = models.TextField(blank=True, default="")
    packing_assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="packing_orders",
    )
    shipping_assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shipping_orders",
    )

    # Added db_index for faster guest order lookups
    full_name = models.CharField(max_length=100)
    email = models.EmailField(db_index=True) 
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)

    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_method = models.CharField(max_length=30, default="razorpay")
    COURIER_CHOICES = [
        ("", "Not set"),
        ("india_post", "India Post"),
        ("delhivery", "Delhivery"),
        ("dtdc", "DTDC"),
        ("bluedart", "Blue Dart"),
        ("other", "Other"),
    ]
    courier_service = models.CharField(
        max_length=30,
        choices=COURIER_CHOICES,
        blank=True,
        default="",
        help_text="Select the courier used for this shipment.",
    )
    consignment_number = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Tracking/consignment number shared with customer.",
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    coins_redeemed = models.PositiveIntegerField(default=0)
    coins_earned_estimate = models.PositiveIntegerField(default=0)
    coins_earned_final = models.PositiveIntegerField(default=0)
    COIN_STATUS_CHOICES = [
        ("none", "None"),
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    coin_status = models.CharField(max_length=20, choices=COIN_STATUS_CHOICES, default="none")
    coin_release_date = models.DateTimeField(blank=True, null=True)
    coin_manual_override = models.BooleanField(default=False)

    # Status
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"

    @property
    def tracking_url(self):
        if self.courier_service == "india_post" and self.consignment_number:
            return "https://www.indiapost.gov.in/"
        return ""


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    allocated_quantity = models.PositiveIntegerField(default=0)
    backordered_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.book.title} × {self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity

# ======================
# WISHLIST ❤️
# ======================

class SearchQueryLog(models.Model):
    query = models.CharField(max_length=255, db_index=True)
    category_slug = models.CharField(max_length=120, blank=True)
    subject_slug = models.CharField(max_length=120, blank=True)
    min_price = models.CharField(max_length=30, blank=True)
    max_price = models.CharField(max_length=30, blank=True)
    rating = models.CharField(max_length=30, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["results_count"]),
        ]

    def __str__(self):
        return f"{self.query} ({self.results_count})"


class UnaniReferenceSource(models.Model):
    name = models.CharField(max_length=140, unique=True)
    citation = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"]),
        ]

    def __str__(self):
        return self.name


class DictionaryQueryLog(models.Model):
    query = models.CharField(max_length=255, db_index=True)
    normalized_query = models.CharField(max_length=255, blank=True, db_index=True)
    results_count = models.PositiveIntegerField(default=0)
    section = models.CharField(max_length=120, blank=True)
    letter = models.CharField(max_length=8, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["results_count"]),
            models.Index(fields=["normalized_query"]),
        ]

    def __str__(self):
        return f"{self.query} ({self.results_count})"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} ♥ {self.book.title}"


# ======================
# SYLLABUS PDFs (DOWNLOADS)
# ======================

class SyllabusPDF(models.Model):
    CATEGORY_CHOICES = [
        ('UG', 'UG Syllabus'),
        ('PG', 'PG Syllabus'),
        ('PRE-TIB', 'Pre-Tib Syllabus'),
    ]

    SEMESTER_CHOICES = [
        ('1', 'First Semester'),
        ('2', 'Second Semester'),
        ('3-6', 'Third to Sixth Semester'),
        ('OTHER', 'General / Other'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    semester = models.CharField(
        max_length=20,
        choices=SEMESTER_CHOICES,
        default='OTHER'
    )
    pdf_file = models.FileField(upload_to='syllabus_pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'semester', 'title']

    def __str__(self):
        return f"{self.category} - {self.title}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("book_price_change", "Book price change"),
        ("book_stock_change", "Book stock change"),
        ("order_paid_change", "Order paid change"),
        ("order_status_change", "Order status change"),
        ("order_update", "Order update"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.model_name} #{self.object_id} - {self.action}"


# ======================
# SITE SETTINGS
# ======================

class SiteSettings(models.Model):
    background_image = models.ImageField(upload_to="site/", blank=True, null=True)
    loader_logo = models.ImageField(upload_to="site/", blank=True, null=True)
    sales_offers_label = models.CharField(max_length=40, default="Sales/Offers")
    sales_offers_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Site Settings #{self.id}"


class IKSCoinsSettings(models.Model):
    name = models.CharField(max_length=80, default="IKS Coins+")
    is_active = models.BooleanField(default=True)
    program_enabled = models.BooleanField(default=True)
    earn_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    max_coins_per_order = models.PositiveIntegerField(default=100)
    monthly_earning_cap = models.PositiveIntegerField(default=300)
    redemption_percentage_limit = models.PositiveSmallIntegerField(default=20)
    minimum_cart_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("300.00"))
    credit_delay_days = models.PositiveSmallIntegerField(default=7)
    registration_bonus = models.PositiveIntegerField(default=25)
    first_purchase_bonus = models.PositiveIntegerField(default=25)
    review_bonus = models.PositiveIntegerField(default=10)
    profile_completion_bonus = models.PositiveIntegerField(default=10)
    disallow_with_coupon = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"


class IKSWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="iks_wallet")
    balance = models.PositiveIntegerField(default=0)
    pending_balance = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_redeemed = models.PositiveIntegerField(default=0)
    monthly_earned = models.PositiveIntegerField(default=0)
    month_key = models.CharField(max_length=7, default="", help_text="YYYY-MM for monthly cap tracking")
    is_frozen = models.BooleanField(default=False)
    is_earning_blocked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"IKS Wallet: {self.user.username}"


class IKSWalletTransaction(models.Model):
    TX_TYPE_CHOICES = [
        ("purchase_reward", "Purchase Reward"),
        ("registration_bonus", "Registration Bonus"),
        ("first_purchase_bonus", "First Purchase Bonus"),
        ("review_reward", "Review Reward"),
        ("profile_completion_reward", "Profile Completion Reward"),
        ("redemption_deduction", "Redemption Deduction"),
        ("manual_adjustment", "Manual Admin Adjustment"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    wallet = models.ForeignKey(IKSWallet, on_delete=models.CASCADE, related_name="transactions")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions")
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="coin_transactions")
    tx_type = models.CharField(max_length=40, choices=TX_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    coins = models.IntegerField(help_text="Positive for credit, negative for deduction.")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    release_date = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "release_date"]),
            models.Index(fields=["tx_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.wallet.user.username} | {self.tx_type} | {self.coins}"


class ClassicalWeightUnit(models.Model):
    classical_weight = models.CharField(max_length=100, unique=True)
    metric_weight = models.CharField(max_length=50, help_text="Example: 170mg, 3.5gm")
    grams_value = models.DecimalField(max_digits=12, decimal_places=6, validators=[MinValueValidator(Decimal("0.000001"))])
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    source_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Classical Weight Unit"
        verbose_name_plural = "Classical Weight Units"

    def __str__(self):
        return f"{self.classical_weight} ({self.metric_weight})"


def _apply_text_watermark(image_field, text):
    if not image_field or not text:
        return False
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False

    try:
        image_field.open()
        img = Image.open(image_field)
    except Exception:
        return False

    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGB")

    draw = ImageDraw.Draw(img)
    width, height = img.size
    font_size = max(12, int(min(width, height) * 0.06))

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except Exception:
        text_width, text_height = draw.textsize(text, font=font)

    margin = max(10, int(min(width, height) * 0.03))
    x = max(margin, width - text_width - margin)
    y = max(margin, height - text_height - margin)

    fill = (255, 255, 255, 180) if img.mode == "RGBA" else (255, 255, 255)
    shadow = (0, 0, 0, 120) if img.mode == "RGBA" else (0, 0, 0)

    draw.text((x + 1, y + 1), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)

    buffer = BytesIO()
    ext = os.path.splitext(image_field.name)[1].lower()
    if ext in (".png", ".webp"):
        fmt = "PNG" if ext == ".png" else "WEBP"
    else:
        fmt = "JPEG"
    img.save(buffer, format=fmt, quality=88)
    buffer.seek(0)

    storage = image_field.storage
    name = image_field.name
    try:
        if storage.exists(name):
            storage.delete(name)
    except Exception:
        pass
    saved_name = storage.save(name, ContentFile(buffer.read()))
    image_field.name = saved_name
    return True

class UnaniTerm(models.Model):
    english_term = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField()
    transliteration = models.CharField(max_length=255, blank=True, db_index=True)
    transliteration_normalized = models.CharField(max_length=255, blank=True, db_index=True, editable=False)
    arabic_script = models.CharField(max_length=255, blank=True, db_index=True)
    arabic_script_normalized = models.CharField(max_length=255, blank=True, db_index=True, editable=False)
    english_term_normalized = models.CharField(max_length=255, blank=True, db_index=True, editable=False)
    section = models.CharField(max_length=120, blank=True, db_index=True)
    reference_source = models.ForeignKey(
        UnaniReferenceSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terms",
    )
    slug = models.SlugField(max_length=255, unique=True, db_index=True, blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["english_term"]
        indexes = [
            models.Index(fields=["english_term"]),
            models.Index(fields=["section", "is_published"]),
            models.Index(fields=["is_published", "created_at"]),
        ]

    def __str__(self):
        return self.english_term

    def save(self, *args, **kwargs):
        self.arabic_script = normalize_script_text(self.arabic_script)
        self.transliteration = normalize_transliteration_text(self.transliteration)
        self.arabic_script_normalized = normalize_script_text(self.arabic_script)
        self.transliteration_normalized = normalize_latin_search_text(self.transliteration)
        self.english_term_normalized = normalize_latin_search_text(self.english_term)
        if not self.slug:
            base = slugify(self.english_term)[:245] or "term"
            candidate = base
            counter = 2
            while UnaniTerm.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                suffix = f"-{counter}"
                candidate = f"{base[:255-len(suffix)]}{suffix}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class DictionaryTermOpenLog(models.Model):
    term = models.ForeignKey(UnaniTerm, on_delete=models.CASCADE, related_name="open_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["term", "created_at"]),
        ]

    def __str__(self):
        return f"{self.term.english_term} @ {self.created_at:%Y-%m-%d}"
