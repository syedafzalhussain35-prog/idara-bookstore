from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.db.models import Q
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import (
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
)
from .forms import CheckoutForm


# ==================================================
# HOME & BOOK LISTING
# ==================================================

def home(request):
    category_slug = request.GET.get('category')
    query = request.GET.get('q')

    books = Book.objects.select_related('category').all()

    if category_slug:
        books = books.filter(category__slug=category_slug)

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    categories = Category.objects.all()

    return render(request, 'store/home.html', {
        'books': books,
        'categories': categories,
        'query': query,
    })


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'store/book_detail.html', {'book': book})


# ==================================================
# AUTHENTICATION
# ==================================================

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'store/signup.html', {'form': form})


def login_page(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.POST.get('next', 'home'))
    else:
        form = AuthenticationForm()

    return render(request, 'store/login.html', {'form': form})


# ==================================================
# WISHLIST
# ==================================================

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.select_related('book').filter(
        user=request.user
    )
    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items,
    })


@login_required
def add_to_wishlist(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        Wishlist.objects.get_or_create(user=request.user, book=book)
    return redirect('wishlist')


@login_required
def remove_from_wishlist(request, book_id):
    if request.method == 'POST':
        Wishlist.objects.filter(
            user=request.user,
            book_id=book_id,
        ).delete()
    return redirect('wishlist')


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
    return render(request, 'store/profile.html', {
        'orders': orders,
    })


# ==================================================
# CART
# ==================================================

@login_required
def add_to_cart(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            book=book,
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    return redirect('cart_detail')


@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('book')
    return render(request, 'store/cart.html', {
        'cart': cart,
        'cart_items': cart_items,
    })


@login_required
def remove_from_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user,
        )
        cart_item.delete()
    return redirect('cart_detail')


# ==================================================
# CHECKOUT & ORDER
# ==================================================

@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if not cart.items.exists():
        return redirect('cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():

            with transaction.atomic():

                # Stock check
                for item in cart.items.select_related('book'):
                    if item.book.stock < item.quantity:
                        return redirect('cart_detail')

                # Create order
                order = form.save(commit=False)
                order.user = request.user
                order.total_cost = sum(
                    item.total_price for item in cart.items.all()
                )
                order.save()

                # Create order items
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        book=item.book,
                        price=item.book.price,
                        quantity=item.quantity,
                    )
                    item.book.stock -= item.quantity
                    item.book.save()

                cart.items.all().delete()

            # Email confirmation
            subject = f'Order Confirmation – Idara Kitab Ul Shifa (# {order.id})'
            html_content = render_to_string(
                'emails/order_confirmation.html',
                {'order': order},
            )

            email = EmailMultiAlternatives(
                subject,
                strip_tags(html_content),
                'idara.kitabulshifa@gmail.com',
                [order.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)

            return render(request, 'store/order_success.html', {
                'order': order,
            })
    else:
        form = CheckoutForm()

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart': cart,
    })


# ==================================================
# STATIC PAGES
# ==================================================

def contact_view(request):
    return render(request, 'store/contact.html')


def about_view(request):
    return render(request, 'store/about.html')


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
