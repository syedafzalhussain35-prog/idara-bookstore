from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.db.models import Sum, F
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
        return total or Decimal('0.00')


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
# ORDERS
# ======================

class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)

    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

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
# WISHLIST
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
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, default='OTHER')
    pdf_file = models.FileField(upload_to='syllabus_pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'semester', 'title']

    def __str__(self):
        return f"{self.category} - {self.title}"
