from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core.mail import EmailMultiAlternatives
import logging
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import requests


from .models import (
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    Review,
    Coupon,
    GalleryItem,
    UserProfile,
)
from .forms import CheckoutForm

logger = logging.getLogger(__name__)


# ==================================================
# EMAILS
# ==================================================

def send_order_confirmation_email(order):
    if not order.email:
        return

    subject = f"Order Confirmation #{order.id} - Idara Kitab Ul Shifa"
    html_body = render_to_string('emails/order_confirmation.html', {'order': order})
    text_body = strip_tags(html_body)

    if settings.BREVO_API_KEY:
        _send_via_brevo(
            to_email=order.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return

    if settings.SENDGRID_API_KEY:
        _send_via_sendgrid(
            to_email=order.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[order.email],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Order email failed to send: %s", exc)


def _send_via_brevo(to_email, subject, text_body, html_body):
    from_email = settings.BREVO_FROM_EMAIL
    from_name = settings.BREVO_FROM_NAME

    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
        "htmlContent": html_body,
    }

    headers = {
        "api-key": settings.BREVO_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code not in (200, 201, 202):
            logger.error("Brevo error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.exception("Brevo request failed: %s", exc)


def _send_via_sendgrid(to_email, subject, text_body, html_body):
    from_email = settings.SENDGRID_FROM_EMAIL
    from_name = settings.SENDGRID_FROM_NAME

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if resp.status_code not in (200, 202):
            logger.error("SendGrid error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.exception("SendGrid request failed: %s", exc)


# ==================================================
# HOME
# ==================================================

def home(request):
    bestsellers = Book.objects.filter(is_bestseller=True)[:8]
    new_arrivals = Book.objects.filter(is_new_arrival=True).order_by('-id')[:8]

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    return render(request, 'store/home.html', {
        'bestsellers': bestsellers,
        'new_arrivals': new_arrivals,
        'wishlist_ids': wishlist_ids,
        'is_homepage': True,
    })


# ==================================================
# CATEGORY PAGE
# ==================================================

def category_books(request, slug):
    category = get_object_or_404(Category, slug=slug)
    books_qs = Book.objects.filter(category=category)

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

    books_qs = Book.objects.filter(
        Q(title__icontains=query) | Q(author__icontains=query)
    ) if query else Book.objects.none()

    paginator = Paginator(books_qs, 12)
    books = paginator.get_page(request.GET.get('page'))

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    return render(request, 'store/search_results.html', {
        'books': books,
        'query': query,
        'wishlist_ids': wishlist_ids,
        'is_homepage': False,
    })


# ==================================================
# BOOK DETAIL + REVIEWS ⭐⭐⭐⭐⭐
# ==================================================

def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    reviews = Review.objects.filter(book=book).select_related('user')
    total_reviews = reviews.count()

    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    # ⭐ Amazon-style rating breakdown
    rating_breakdown = []
    for star in range(5, 0, -1):
        count = reviews.filter(rating=star).count()
        percent = int((count / total_reviews) * 100) if total_reviews else 0
        rating_breakdown.append({
            'stars': star,
            'count': count,
            'percent': percent,
        })

    has_purchased = (
        request.user.is_authenticated and
        OrderItem.objects.filter(
            order__user=request.user,
            book=book
        ).exists()
    )

    return render(request, 'store/book_detail.html', {
        'book': book,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_breakdown': rating_breakdown,
        'has_purchased': has_purchased,
    })


@login_required
@require_POST
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # ✔ Only verified buyers
    if not OrderItem.objects.filter(order__user=request.user, book=book).exists():
        return redirect('book_detail', book_id=book.id)

    Review.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={
            'rating': int(request.POST.get('rating')),
            'comment': request.POST.get('comment', '').strip()
        }
    )

    return redirect('book_detail', book_id=book.id)


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
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
@require_POST
def wishlist_toggle(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    obj, created = Wishlist.objects.get_or_create(user=request.user, book=book)

    if created:
        return JsonResponse({'status': 'added'})
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
    Wishlist.objects.filter(user=request.user, book_id=book_id).delete()
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


# ==================================================
# PROFILE
# ==================================================

@login_required
def profile_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        zip_code = request.POST.get("zip_code", "").strip()
        company = request.POST.get("company", "").strip()

        has_error = False

        if username and username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, "Username already taken.")
                has_error = True
            else:
                user.username = username

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, "Email already in use.")
                has_error = True
            else:
                user.email = email

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        profile.phone = phone
        profile.address = address
        profile.city = city
        profile.zip_code = zip_code
        profile.company = company
        profile.save()

        if not has_error:
            messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    orders = Order.objects.filter(user=user).prefetch_related('items__book')
    return render(request, 'store/profile.html', {
        'orders': orders,
        'profile': profile,
    })


# ==================================================
# CART
# ==================================================

def _get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    cart_id = request.session.get('cart_id')
    cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
    if cart:
        return cart

    cart = Cart.objects.create(user=None)
    request.session['cart_id'] = cart.id
    request.session.modified = True
    return cart


def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart = _get_or_create_cart(request)

    item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    if not created:
        item.quantity += 1
        item.save()

    return redirect('cart_detail')


def cart_detail(request):
    cart = _get_or_create_cart(request)
    return render(request, 'store/cart.html', {
        'cart': cart,
        'cart_items': cart.items.select_related('book'),
    })


def remove_from_cart(request, item_id):
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    return redirect('cart_detail')


# ==================================================
# CHECKOUT + AUTO USER HANDLING 🧾
# ==================================================
def checkout(request):
    # 🛒 Cart handling
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        # Better Guest logic: Check session for a temporary cart ID
        cart_id = request.session.get('cart_id')
        cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
    
    if not cart or not cart.items.exists():
        return redirect('cart_detail')

    if request.method == "POST":
        email = request.POST.get("email")
        full_name = request.POST.get("full_name")
        
        # 🔐 AUTO USER HANDLING
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            # Atomic check to prevent duplicate user creation under high load
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"username": email}
            )

            if created:
                password = get_random_string(10)
                user.set_password(password)
                user.save()
            
            # Attach the guest cart to the newly created user
            cart.user = user
            cart.save()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # 🧾 CREATE ORDER
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                full_name=full_name,
                email=email,
                mobile=request.POST.get("mobile"),
                address=request.POST.get("address"),
                city=request.POST.get("city"),
                zip_code=request.POST.get("zip_code"),
                total_cost=cart.get_total(), 
                is_paid=False,
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    book=item.book,
                    price=item.book.price,
                    quantity=item.quantity
                )
                # 📦 Update Stock
                if item.book.stock >= item.quantity:
                    item.book.stock -= item.quantity
                    item.book.save()

            # 🧹 Clear cart
            cart.items.all().delete()
            # Clean up guest session
            if 'cart_id' in request.session:
                del request.session['cart_id']

        # Send confirmation email (best-effort)
        send_order_confirmation_email(order)

        return render(request, 'store/order_success.html', {'order': order})

    return render(request, "store/checkout.html", {'cart': cart})
# ==================================================
# STATIC & POLICY PAGES
# ==================================================

def about_view(request): return render(request, 'store/about.html')
def contact_view(request): return render(request, 'store/contact.html')
def gallery_view(request):
    items = GalleryItem.objects.all().order_by('event', 'order', 'id')
    events = []
    current_event = None

    for item in items:
        if current_event != item.event:
            events.append({
                'name': item.event,
                'items': [],
            })
            current_event = item.event
        events[-1]['items'].append(item)

    return render(request, 'store/gallery.html', {
        'events': events,
    })

def refund_policy(request): return render(request, 'store/policies/refund.html')
def shipping_policy(request): return render(request, 'store/policies/shipping.html')
def privacy_policy(request): return render(request, 'store/policies/privacy.html')
def terms_policy(request): return render(request, 'store/policies/terms.html')
def returns_policy(request): return render(request, 'store/policies/returns.html')

def publish_with_us(request): return render(request, 'store/publish_with_us.html')

# ==================================================
# 🔍 LIVE SEARCH (AJAX)
# ==================================================

from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def live_search(request):
    q = request.GET.get('q', '').strip()
    results = []

    if len(q) < 2:
        return JsonResponse({'results': []})

    books = (
        Book.objects
        .filter(
            Q(title__icontains=q) |
            Q(author__icontains=q)
        )
        .distinct()[:20]
    )

    ranked = []
    for book in books:
        score = max(
            similarity(q, book.title),
            similarity(q, book.author)
        )
        if score > 0.35:  # Roman-Urdu tolerance
            ranked.append((score, book))

    ranked.sort(key=lambda x: x[0], reverse=True)

    for score, book in ranked[:8]:
        results.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'url': f"/book/{book.id}/",
            'image': book.main_cover.url if book.main_cover else '',
        })

    return JsonResponse({'results': results})
