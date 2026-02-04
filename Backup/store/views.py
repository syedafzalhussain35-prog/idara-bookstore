from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    SyllabusPDF,
)
from .forms import CheckoutForm


# ==================================================
# HOME
# ==================================================

def home(request):
    bestsellers = (
        Book.objects
        .filter(is_bestseller=True)
        .select_related('category')[:8]
    )

    new_arrivals = (
        Book.objects
        .filter(is_new_arrival=True)
        .select_related('category')
        .order_by('-id')[:8]
    )

    return render(request, 'store/home.html', {
        'bestsellers': bestsellers,
        'new_arrivals': new_arrivals,
        'is_homepage': True,
    })


# ==================================================
# CATEGORY PAGE
# ==================================================

def category_books(request, slug):
    category = get_object_or_404(Category, slug=slug)
    books_qs = Book.objects.filter(category=category).select_related('category')

    query = request.GET.get('q', '').strip()
    if query:
        books_qs = books_qs.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    sort = request.GET.get('sort')
    if sort == 'newest':
        books_qs = books_qs.order_by('-created_at')
    elif sort == 'price_low':
        books_qs = books_qs.order_by('price')
    elif sort == 'price_high':
        books_qs = books_qs.order_by('-price')
    elif sort == 'bestseller':
        books_qs = books_qs.filter(is_bestseller=True)

    paginator = Paginator(books_qs, 12)
    books = paginator.get_page(request.GET.get('page'))

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    return render(request, 'store/category_books.html', {
        'category': category,
        'books': books,
        'query': query,
        'sort': sort,
        'wishlist_ids': wishlist_ids,
        'is_homepage': False,
    })


# ==================================================
# SEARCH
# ==================================================

def search(request):
    query = request.GET.get('q', '').strip()

    books_qs = (
        Book.objects
        .filter(Q(title__icontains=query) | Q(author__icontains=query))
        .select_related('category')
        if query else Book.objects.none()
    )

    paginator = Paginator(books_qs, 12)
    books = paginator.get_page(request.GET.get('page'))

    return render(request, 'store/search_results.html', {
        'books': books,
        'query': query,
        'is_homepage': False,
    })


# ==================================================
# BOOK DETAIL
# ==================================================

def book_detail(request, book_id):
    book = get_object_or_404(
        Book.objects.prefetch_related('images'),
        id=book_id
    )

    is_wishlisted = (
        request.user.is_authenticated and
        Wishlist.objects.filter(user=request.user, book=book).exists()
    )

    return render(request, 'store/book_detail.html', {
        'book': book,
        'is_wishlisted': is_wishlisted,
    })


# ==================================================
# AUTH
# ==================================================

def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('home')
    return render(request, 'store/signup.html', {'form': form})


def login_page(request):
    form = AuthenticationForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', 'home'))
    return render(request, 'store/login.html', {'form': form})


# ==================================================
# WISHLIST
# ==================================================

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.select_related('book').filter(user=request.user)
    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items
    })


@login_required
@require_POST
def wishlist_toggle(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    obj, created = Wishlist.objects.get_or_create(
        user=request.user,
        book=book
    )

    if created:
        return JsonResponse({'status': 'added'})
    else:
        obj.delete()
        return JsonResponse({'status': 'removed'})


@login_required
def add_to_wishlist(request, book_id):
    Wishlist.objects.get_or_create(
        user=request.user,
        book=get_object_or_404(Book, id=book_id)
    )
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def remove_from_wishlist(request, book_id):
    Wishlist.objects.filter(
        user=request.user,
        book_id=book_id
    ).delete()
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


# ==================================================
# PROFILE
# ==================================================

@login_required
def profile_view(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__book')
        .order_by('-created_at')
    )
    return render(request, 'store/profile.html', {'orders': orders})


# ==================================================
# CART
# ==================================================

@login_required
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    if not created:
        item.quantity += 1
        item.save()

    return redirect('cart_detail')


@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {
        'cart': cart,
        'cart_items': cart.items.select_related('book'),
    })


@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(
        id=item_id,
        cart__user=request.user
    ).delete()
    return redirect('cart_detail')


# ==================================================
# CHECKOUT
# ==================================================

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        return redirect('cart_detail')

    form = CheckoutForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.total_cost = cart.get_total()
                order.save()

                for item in cart.items.select_related('book'):
                    if item.book.stock < item.quantity:
                        raise ValueError(f"Insufficient stock for {item.book.title}")

                    OrderItem.objects.create(
                        order=order,
                        book=item.book,
                        price=item.book.price,
                        quantity=item.quantity
                    )

                    item.book.stock -= item.quantity
                    item.book.save()

                cart.items.all().delete()

            return render(request, 'store/order_success.html', {'order': order})

        except ValueError as e:
            form.add_error(None, str(e))

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart': cart,
    })


# ==================================================
# DOWNLOADS
# ==================================================

def download_list(request):
    pdfs = SyllabusPDF.objects.all()

    if request.GET.get('cat'):
        pdfs = pdfs.filter(category=request.GET['cat'])

    if request.GET.get('sem'):
        pdfs = pdfs.filter(semester=request.GET['sem'])

    return render(request, 'store/downloads.html', {
        'pdfs': pdfs,
        'selected_category': request.GET.get('cat'),
        'selected_semester': request.GET.get('sem'),
        'is_homepage': False,
    })


# ==================================================
# STATIC PAGES
# ==================================================

def about_view(request):
    return render(request, 'store/about.html')


def contact_view(request):
    return render(request, 'store/contact.html')


def gallery_view(request):
    return render(request, 'store/gallery.html')


# ==================================================
# POLICY PAGES
# ==================================================

def refund_policy(request):
    return render(request, 'store/policies/refund.html')


def shipping_policy(request):
    return render(request, 'store/policies/shipping.html')


def privacy_policy(request):
    return render(request, 'store/policies/privacy.html')


def terms_policy(request):
    return render(request, 'store/policies/terms.html')


def returns_policy(request):
    return render(request, 'store/policies/returns.html')
