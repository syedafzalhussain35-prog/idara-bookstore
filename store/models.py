from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, F, Avg
from decimal import Decimal


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
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
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
    description = models.TextField(blank=True, null=True)
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

    is_bestseller = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=True)

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


class BookImage(models.Model):
    book = models.ForeignKey(
        Book,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='books/gallery/')

    def __str__(self):
        return f"Image for {self.book.title}"


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
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
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
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    focal_x = models.PositiveSmallIntegerField(default=50)
    focal_y = models.PositiveSmallIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title or f"Banner {self.id}"

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
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


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
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # Added db_index for faster guest order lookups
    full_name = models.CharField(max_length=100)
    email = models.EmailField(db_index=True) 
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)

    # Pricing
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


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.book.title} × {self.quantity}"

# ======================
# WISHLIST ❤️
# ======================

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
