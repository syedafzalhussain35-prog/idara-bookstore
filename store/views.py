from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.core import signing
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Sum, Value
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.conf import settings
from django.core.cache import cache
import logging
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re


from .models import (
    Book,
    Bundle,
    Cart,
    CartItem,
    CartBundleItem,
    Order,
    OrderItem,
    Wishlist,
    Category,
    Subject,
    Review,
    Coupon,
    GalleryItem,
    UserProfile,
    UserAddress,
    PublishWithUsSubmission,
    Banner,
    SearchQueryLog,
    UnaniTerm,
)
from .email_utils import send_publish_with_us
from .tasks import enqueue_order_confirmation, enqueue_order_alert
from .coins import (
    get_coin_settings,
    get_wallet,
    get_max_redeemable,
    estimate_purchase_coins,
    apply_redemption_for_order,
    queue_order_pending_rewards,
    process_due_pending_rewards_for_user,
    award_review_bonus_if_eligible,
    award_profile_completion_bonus_if_eligible,
)

logger = logging.getLogger(__name__)

RECENTLY_VIEWED_LIMIT = 10
DICTIONARY_SCRIPT_LETTERS = [
    "ا", "آ", "ب", "پ", "ت", "ٹ", "ث", "ج", "چ", "ح", "خ",
    "د", "ڈ", "ذ", "ر", "ڑ", "ز", "ژ", "س", "ش", "ص", "ض",
    "ط", "ظ", "ع", "غ", "ف", "ق", "ک", "گ", "ل", "م", "ن",
    "ں", "و", "ہ", "ھ", "ء", "ی", "ے",
]


def _is_mobile_request(request):
    ua = (request.META.get("HTTP_USER_AGENT") or "").lower()
    return bool(re.search(r"android|iphone|ipod|mobile|opera mini|iemobile", ua))


def _get_razorpay_client():
    if not getattr(settings, "RAZORPAY_ENABLED", False):
        logger.warning("Razorpay is disabled due to missing keys in settings.")
        return None
    try:
        import razorpay
    except Exception:
        logger.exception("Failed to import razorpay package.")
        return None
    try:
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except Exception:
        logger.exception("Failed to initialize razorpay client.")
        return None


def _update_recently_viewed(request, book_id):
    viewed = request.session.get("recently_viewed", [])
    try:
        viewed = [int(bid) for bid in viewed if str(bid).isdigit()]
    except (ValueError, TypeError):
        viewed = []

    if book_id in viewed:
        viewed.remove(book_id)
    viewed.insert(0, book_id)
    viewed = viewed[:RECENTLY_VIEWED_LIMIT]
    request.session["recently_viewed"] = viewed
    request.session.modified = True


def _get_recently_viewed(request, exclude_id=None, limit=8):
    ids = request.session.get("recently_viewed", [])
    if exclude_id:
        ids = [bid for bid in ids if bid != exclude_id]
    if not ids:
        return []
    preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(ids)], output_field=IntegerField())
    return list(Book.objects.filter(id__in=ids).order_by(preserved)[:limit])


# ==================================================
# CACHE HELPERS
# ==================================================

def _ordered_by_ids(model, ids):
    if not ids:
        return model.objects.none()
    preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(ids)], output_field=IntegerField())
    return model.objects.filter(id__in=ids).order_by(preserved)


def _recommended_books(limit=6, exclude_ids=None):
    exclude_ids = exclude_ids or []
    qs = Book.objects.filter(stock__gt=0).exclude(id__in=exclude_ids)
    qs = qs.order_by("-is_bestseller", "-is_trending", "-created_at")
    return qs[:limit]


def _bundle_max_quantity(bundle):
    stocks = list(bundle.books.values_list("stock", flat=True))
    if not stocks:
        return 0
    return min(stocks)


def _validate_cart_stock(cart):
    issues = []
    for item in cart.items.select_related("book").all():
        if item.quantity > item.book.stock:
            issues.append(f"{item.book.title} (available: {item.book.stock})")
    for bitem in cart.bundle_items.select_related("bundle").all():
        available = _bundle_max_quantity(bitem.bundle)
        if bitem.quantity > available:
            issues.append(f"{bitem.bundle.name} bundle (available: {available})")
    return issues


def _cache_get_ids(key, queryset, ttl):
    cached_ids = cache.get(key)
    if cached_ids is not None:
        return cached_ids
    ids = list(queryset.values_list("id", flat=True))
    cache.set(key, ids, ttl)
    return ids


def _to_decimal(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _apply_price_rating_filters(queryset, min_price_raw="", max_price_raw="", rating_raw=""):
    min_price = _to_decimal(min_price_raw)
    max_price = _to_decimal(max_price_raw)
    rating = _to_decimal(rating_raw)

    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)
    if rating is not None:
        queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=rating)
    return queryset


# ==================================================
# HOME
# ==================================================

def home(request):
    cache_ttl = getattr(settings, "HOME_CACHE_TTL", 120)
    is_mobile = _is_mobile_request(request)

    if is_mobile:
        banner_ids = _cache_get_ids(
            "home:banners:mobile",
            Banner.objects.filter(is_active=True, show_on_mobile=True).order_by("order", "id"),
            cache_ttl,
        )
        # Backward-compatible fallback for existing data created before
        # device flags were introduced (mobile flag defaulted to False).
        if not banner_ids:
            banner_ids = _cache_get_ids(
                "home:banners:mobile:fallback",
                Banner.objects.filter(is_active=True, show_on_desktop=True).order_by("order", "id"),
                cache_ttl,
            )
    else:
        banner_ids = _cache_get_ids(
            "home:banners:desktop",
            Banner.objects.filter(is_active=True, show_on_desktop=True).order_by("order", "id"),
            cache_ttl,
        )

    banners = _ordered_by_ids(Banner, banner_ids)

    featured_ids = _cache_get_ids(
        "home:featured",
        Book.objects.filter(is_featured=True).order_by("-id")[:8],
        cache_ttl,
    )
    featured_books = list(_ordered_by_ids(Book, featured_ids))

    bestseller_ids = _cache_get_ids(
        "home:bestsellers",
        Book.objects.filter(is_bestseller=True).order_by("-id")[:8],
        cache_ttl,
    )
    bestsellers = list(_ordered_by_ids(Book, bestseller_ids))

    trending_ids = _cache_get_ids(
        "home:trending",
        Book.objects.filter(is_trending=True).order_by("-id")[:8],
        cache_ttl,
    )
    trending_books = list(_ordered_by_ids(Book, trending_ids))

    new_ids = _cache_get_ids(
        "home:new_arrivals",
        Book.objects.filter(is_new_arrival=True).order_by("-id")[:8],
        cache_ttl,
    )
    new_arrivals = list(_ordered_by_ids(Book, new_ids))
    recently_viewed = _get_recently_viewed(request, limit=8)
    bundle_ids = _cache_get_ids(
        "home:bundles",
        Bundle.objects.filter(is_active=True).order_by("-id")[:8],
        cache_ttl,
    )
    bundles = list(_ordered_by_ids(Bundle, bundle_ids))

    subject_ids = _cache_get_ids(
        "home:subjects",
        Subject.objects.filter(is_active=True).order_by("name")[:8],
        cache_ttl,
    )
    subjects = list(_ordered_by_ids(Subject, subject_ids))

    popular_ids = _cache_get_ids(
        "home:popular",
        Book.objects.annotate(sales=Sum("orderitem__quantity")).order_by("-sales", "-id")[:8],
        cache_ttl,
    )
    popular_books = list(_ordered_by_ids(Book, popular_ids))

    recommended = []
    if recently_viewed:
        viewed_ids = [b.id for b in recently_viewed]
        category_ids = [b.category_id for b in recently_viewed if b.category_id]
        subject_ids = list(
            Book.objects.filter(id__in=viewed_ids).values_list("subjects__id", flat=True)
        )
        recommended_qs = (
            Book.objects
            .filter(Q(category_id__in=category_ids) | Q(subjects__id__in=subject_ids))
            .exclude(id__in=viewed_ids)
            .distinct()
            .order_by("-is_bestseller", "-id")
        )
        recommended = list(recommended_qs[:8])

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    coupons = [c for c in Coupon.objects.filter(active=True).order_by("-created_at")[:6] if c.is_valid()]

    return render(request, 'store/home.html', {
        'banners': banners,
        'featured_books': featured_books,
        'bestsellers': bestsellers,
        'trending_books': trending_books,
        'new_arrivals': new_arrivals,
        'popular_books': popular_books,
        'recommended_books': recommended,
        'recently_viewed': recently_viewed,
        'bundles': bundles,
        'subjects': subjects,
        'wishlist_ids': wishlist_ids,
        'coupons': coupons,
        'is_homepage': True,
    })


def offers_view(request):
    coupons = [c for c in Coupon.objects.filter(active=True).order_by("-created_at") if c.is_valid()]
    return render(request, "store/offers.html", {"coupons": coupons})


# ==================================================
# CATEGORY PAGE
# ==================================================

def category_books(request, slug):
    if not request.user.is_authenticated:
        cache_key = f"category:{slug}:{request.GET.urlencode() or 'all'}"
        cached = cache.get(cache_key)
        if cached:
            return cached

    category = get_object_or_404(Category, slug=slug)
    books_qs = Book.objects.filter(category=category)

    query = request.GET.get('q', '').strip()
    if query:
        books_qs = books_qs.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query)
        )

    author = request.GET.get('author', '').strip()
    if author:
        books_qs = books_qs.filter(author__icontains=author)

    subject_slug = request.GET.get('subject', '').strip()
    if subject_slug:
        books_qs = books_qs.filter(subjects__slug=subject_slug)

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    rating = request.GET.get('rating', '').strip()

    books_qs = _apply_price_rating_filters(
        books_qs,
        min_price_raw=min_price,
        max_price_raw=max_price,
        rating_raw=rating,
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

    subjects = Subject.objects.filter(is_active=True).order_by('name')

    response = render(request, 'store/category_books.html', {
        'category': category,
        'books': books,
        'query': query,
        'subject_slug': subject_slug,
        'min_price': min_price,
        'max_price': max_price,
        'rating': rating,
        'sort': sort,
        'subjects': subjects,
        'wishlist_ids': wishlist_ids,
        'is_homepage': False,
    })
    if not request.user.is_authenticated:
        cache.set(cache_key, response, getattr(settings, "CATEGORY_CACHE_TTL", 120))
    return response


# ==================================================
# SEARCH
# ==================================================

def search(request):
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    subject_slug = request.GET.get('subject', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    rating = request.GET.get('rating', '').strip()

    books_qs = Book.objects.filter(
        Q(title__icontains=query) | Q(author__icontains=query)
    ) if query else Book.objects.none()

    if category_slug:
        books_qs = books_qs.filter(category__slug=category_slug)

    if subject_slug:
        books_qs = books_qs.filter(subjects__slug=subject_slug)

    books_qs = _apply_price_rating_filters(
        books_qs,
        min_price_raw=min_price,
        max_price_raw=max_price,
        rating_raw=rating,
    )

    results_count = books_qs.count() if query else 0

    if query:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if not ip:
            ip = request.META.get("REMOTE_ADDR")
        SearchQueryLog.objects.create(
            query=query,
            category_slug=category_slug,
            subject_slug=subject_slug,
            min_price=min_price,
            max_price=max_price,
            rating=rating,
            results_count=results_count,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip or None,
        )

    paginator = Paginator(books_qs, 12)
    books = paginator.get_page(request.GET.get('page'))

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    has_filters = bool(subject_slug or min_price or max_price or rating)
    return render(request, 'store/search_results.html', {
        'books': books,
        'query': query,
        'category_slug': category_slug,
        'subject_slug': subject_slug,
        'min_price': min_price,
        'max_price': max_price,
        'rating': rating,
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'wishlist_ids': wishlist_ids,
        'has_filters': has_filters,
        'suggested_books': _recommended_books(limit=8),
        'is_homepage': False,
    })


def dictionary_list(request):
    query = (request.GET.get("q") or "").strip()
    selected_section = (request.GET.get("section") or "").strip()
    selected_letter = (request.GET.get("letter") or "").strip()

    terms_qs = UnaniTerm.objects.filter(is_published=True)

    if query:
        terms_qs = terms_qs.filter(
            Q(english_term__icontains=query)
            | Q(transliteration__icontains=query)
            | Q(arabic_script__icontains=query)
            | Q(description__icontains=query)
        )
        # Prioritize native script matches for Unani usage patterns.
        terms_qs = terms_qs.annotate(
            match_priority=Case(
                When(arabic_script__icontains=query, then=Value(1)),
                When(transliteration__icontains=query, then=Value(2)),
                When(english_term__icontains=query, then=Value(3)),
                When(description__icontains=query, then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            )
        ).order_by("match_priority", "arabic_script", "transliteration", "english_term")

    all_sections = list(
        UnaniTerm.objects.filter(is_published=True)
        .exclude(section="")
        .values_list("section", flat=True)
        .distinct()
        .order_by("section")
    )
    if selected_section and selected_section in all_sections:
        terms_qs = terms_qs.filter(section=selected_section)
    else:
        selected_section = ""

    if selected_letter and selected_letter in DICTIONARY_SCRIPT_LETTERS:
        terms_qs = terms_qs.filter(arabic_script__startswith=selected_letter)
    else:
        selected_letter = ""

    # Script-first ordering for a Unani Urdu/Arabic/Persian dictionary.
    terms_qs = terms_qs.annotate(
        script_priority=Case(
            When(arabic_script="", then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("script_priority", "arabic_script", "transliteration", "english_term")

    total_published = UnaniTerm.objects.filter(is_published=True).count()
    page_size = int(getattr(settings, "DICTIONARY_PAGE_SIZE", 20))
    paginator = Paginator(terms_qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "store/dictionary_list.html", {
        "page_obj": page_obj,
        "query": query,
        "selected_section": selected_section,
        "selected_letter": selected_letter,
        "letters": DICTIONARY_SCRIPT_LETTERS,
        "sections": all_sections,
        "total_published": total_published,
    })


def dictionary_detail(request, slug):
    term = get_object_or_404(UnaniTerm, slug=slug, is_published=True)
    description_snippet = strip_tags(term.description or "").strip()
    meta_description = description_snippet[:150]
    if len(description_snippet) > 150:
        meta_description += "..."

    return render(request, "store/dictionary_detail.html", {
        "term": term,
        "meta_title": f"{term.english_term} Meaning in Unani | IKS Dictionary",
        "meta_description": meta_description,
    })


# ==================================================
# SUBJECT PAGE
# ==================================================

def subject_books(request, slug):
    if not request.user.is_authenticated:
        cache_key = f"subject:{slug}:{request.GET.urlencode() or 'all'}"
        cached = cache.get(cache_key)
        if cached:
            return cached

    subject = get_object_or_404(Subject, slug=slug, is_active=True)
    books_qs = Book.objects.filter(subjects=subject)

    query = request.GET.get('q', '').strip()
    if query:
        books_qs = books_qs.filter(Q(title__icontains=query) | Q(author__icontains=query))

    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        books_qs = books_qs.filter(category__slug=category_slug)

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    rating = request.GET.get('rating', '').strip()

    books_qs = _apply_price_rating_filters(
        books_qs,
        min_price_raw=min_price,
        max_price_raw=max_price,
        rating_raw=rating,
    )

    paginator = Paginator(books_qs, 12)
    books = paginator.get_page(request.GET.get('page'))

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list('book_id', flat=True)

    response = render(request, 'store/subject_books.html', {
        'subject': subject,
        'books': books,
        'query': query,
        'category_slug': category_slug,
        'min_price': min_price,
        'max_price': max_price,
        'rating': rating,
        'subjects': Subject.objects.filter(is_active=True).order_by('name'),
        'wishlist_ids': wishlist_ids,
        'is_homepage': False,
    })
    if not request.user.is_authenticated:
        cache.set(cache_key, response, getattr(settings, "CATEGORY_CACHE_TTL", 120))
    return response


# ==================================================
# BOOK DETAIL + REVIEWS ⭐⭐⭐⭐⭐
# ==================================================

def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    _update_recently_viewed(request, book.id)

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

    related_books = []
    if book.category_id:
        related_books = list(
            Book.objects
            .filter(category=book.category)
            .exclude(id=book.id)
            .order_by("-is_bestseller", "-id")[:8]
        )

    if len(related_books) < 4:
        exclude_ids = [book.id] + [b.id for b in related_books]
        fallback = list(
            Book.objects
            .filter(is_bestseller=True)
            .exclude(id__in=exclude_ids)
            .order_by("-id")[:8 - len(related_books)]
        )
        related_books += fallback

    recently_viewed = _get_recently_viewed(request, exclude_id=book.id, limit=8)

    co_purchase = (
        OrderItem.objects
        .filter(order__items__book=book)
        .exclude(book=book)
        .values("book")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    co_ids = [row["book"] for row in co_purchase]
    people_also_bought = list(_ordered_by_ids(Book, co_ids))

    return render(request, 'store/book_detail.html', {
        'book': book,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_breakdown': rating_breakdown,
        'has_purchased': has_purchased,
        'related_books': related_books,
        'recently_viewed': recently_viewed,
        'people_also_bought': people_also_bought,
    })


@login_required
@require_POST
def add_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # ✔ Only verified buyers
    if not OrderItem.objects.filter(order__user=request.user, book=book).exists():
        return redirect('book_detail', book_id=book.id)

    review, _ = Review.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={
            'rating': int(request.POST.get('rating')),
            'comment': request.POST.get('comment', '').strip()
        }
    )
    award_review_bonus_if_eligible(request.user, review.book)

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
    exclude_ids = [item.book_id for item in wishlist_items]
    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items,
        'suggested_books': _recommended_books(limit=6, exclude_ids=exclude_ids),
    })


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
        iks_follow_instagram = bool(request.POST.get("iks_follow_instagram"))
        iks_follow_facebook = bool(request.POST.get("iks_follow_facebook"))

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
        profile.iks_follow_instagram = iks_follow_instagram
        profile.iks_follow_facebook = iks_follow_facebook
        profile.save()
        award_profile_completion_bonus_if_eligible(user)

        if not has_error:
            messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    orders = Order.objects.filter(user=user).prefetch_related('items__book')
    addresses = UserAddress.objects.filter(user=user)
    process_due_pending_rewards_for_user(user)
    wallet = get_wallet(user)
    coin_transactions = wallet.transactions.select_related("order", "book")[:40]
    return render(request, 'store/profile.html', {
        'orders': orders,
        'profile': profile,
        'addresses': addresses,
        'wallet': wallet,
        'coin_settings': get_coin_settings(),
        'coin_transactions': coin_transactions,
    })


@login_required
@require_POST
def add_address(request):
    label = request.POST.get("label", "Home").strip() or "Home"
    full_name = request.POST.get("full_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    address = request.POST.get("address", "").strip()
    city = request.POST.get("city", "").strip()
    zip_code = request.POST.get("zip_code", "").strip()
    is_default = bool(request.POST.get("is_default"))

    if not address or not city:
        messages.error(request, "Address and city are required.")
        return redirect("profile")

    if is_default:
        UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)

    UserAddress.objects.create(
        user=request.user,
        label=label,
        full_name=full_name,
        phone=phone,
        address=address,
        city=city,
        zip_code=zip_code,
        is_default=is_default,
    )
    messages.success(request, "Address saved.")
    return redirect("profile")


@login_required
@require_POST
def set_default_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default"])
    messages.success(request, "Default address updated.")
    return redirect("profile")


@login_required
@require_POST
def delete_address(request, address_id):
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted.")
    return redirect("profile")


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

    if book.stock < 1:
        messages.error(request, "This book is out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'cart_detail'))

    item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    if created:
        if item.quantity > book.stock:
            item.quantity = book.stock
            item.save(update_fields=["quantity"])
        return redirect('cart_detail')

    if item.quantity >= book.stock:
        messages.warning(request, f"Only {book.stock} copy/copies available for {book.title}.")
        return redirect('cart_detail')

    item.quantity += 1
    item.save(update_fields=["quantity"])
    return redirect('cart_detail')


def cart_detail(request):
    cart = _get_or_create_cart(request)
    has_cart_items = cart.items.exists() or cart.bundle_items.exists()
    exclude_ids = list(cart.items.values_list("book_id", flat=True))
    return render(request, 'store/cart.html', {
        'cart': cart,
        'cart_items': cart.items.select_related('book'),
        'bundle_items': cart.bundle_items.select_related('bundle'),
        'has_cart_items': has_cart_items,
        'suggested_books': _recommended_books(limit=6, exclude_ids=exclude_ids),
    })


def update_cart_item(request, item_id, action):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    if action == "plus":
        if item.book.stock < 1:
            messages.error(request, f"{item.book.title} is out of stock.")
            item.delete()
            return redirect("cart_detail")
        if item.quantity >= item.book.stock:
            messages.warning(request, f"Only {item.book.stock} copy/copies available for {item.book.title}.")
            return redirect("cart_detail")
        item.quantity += 1
        item.save(update_fields=["quantity"])
    elif action == "minus":
        if item.quantity > 1:
            item.quantity -= 1
            item.save(update_fields=["quantity"])
        else:
            item.delete()
    return redirect("cart_detail")


def update_bundle_item(request, item_id, action):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartBundleItem, id=item_id, cart=cart)
    if action == "plus":
        available = _bundle_max_quantity(item.bundle)
        if available < 1:
            messages.error(request, f"{item.bundle.name} bundle is out of stock.")
            item.delete()
            return redirect("cart_detail")
        if item.quantity >= available:
            messages.warning(request, f"Only {available} copy/copies available for {item.bundle.name} bundle.")
            return redirect("cart_detail")
        item.quantity += 1
        item.save(update_fields=["quantity"])
    elif action == "minus":
        if item.quantity > 1:
            item.quantity -= 1
            item.save(update_fields=["quantity"])
        else:
            item.delete()
    return redirect("cart_detail")


def remove_from_cart(request, item_id):
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(id=item_id, cart=cart).delete()
    return redirect('cart_detail')


def add_bundle_to_cart(request, bundle_id):
    bundle = get_object_or_404(Bundle, id=bundle_id, is_active=True)
    cart = _get_or_create_cart(request)
    available = _bundle_max_quantity(bundle)

    if available < 1:
        messages.error(request, f"{bundle.name} bundle is out of stock.")
        return redirect(request.META.get('HTTP_REFERER', 'cart_detail'))

    item, created = CartBundleItem.objects.get_or_create(cart=cart, bundle=bundle)
    if created:
        if item.quantity > available:
            item.quantity = available
            item.save(update_fields=["quantity"])
        return redirect('cart_detail')

    if item.quantity >= available:
        messages.warning(request, f"Only {available} copy/copies available for {bundle.name} bundle.")
        return redirect('cart_detail')

    item.quantity += 1
    item.save(update_fields=["quantity"])
    return redirect('cart_detail')


def remove_bundle_from_cart(request, item_id):
    cart = _get_or_create_cart(request)
    CartBundleItem.objects.filter(id=item_id, cart=cart).delete()
    return redirect('cart_detail')


@login_required
@require_POST
def reorder_order(request, order_id):
    source_order = get_object_or_404(Order.objects.prefetch_related("items__book"), id=order_id, user=request.user)
    cart = _get_or_create_cart(request)
    added = 0
    skipped = 0
    for order_item in source_order.items.all():
        book = order_item.book
        if book.stock <= 0:
            skipped += 1
            continue
        cart_item, _ = CartItem.objects.get_or_create(cart=cart, book=book)
        max_addable = max(book.stock - cart_item.quantity, 0)
        qty_to_add = min(order_item.quantity, max_addable)
        if qty_to_add <= 0:
            skipped += 1
            continue
        cart_item.quantity += qty_to_add
        cart_item.save(update_fields=["quantity"])
        added += qty_to_add

    if added:
        messages.success(request, f"Reorder added ({added} item(s)) to your cart.")
    if skipped:
        messages.warning(request, f"{skipped} item(s) skipped due to stock limits.")
    if not added and not skipped:
        messages.info(request, "No items available to reorder.")
    return redirect("cart_detail")


def _calculate_checkout_totals(cart):
    subtotal = cart.get_total()
    discount_amount = Decimal("0.00")
    for item in cart.items.select_related("book").all():
        if item.book.mrp_price and item.book.mrp_price > item.book.price:
            discount_amount += (item.book.mrp_price - item.book.price) * item.quantity
    for bitem in cart.bundle_items.select_related("bundle").all():
        original_total = bitem.bundle.original_total
        if original_total and original_total > bitem.bundle.bundle_price:
            discount_amount += (original_total - bitem.bundle.bundle_price) * bitem.quantity

    shipping_base = Decimal(str(getattr(settings, "SHIPPING_FLAT", 0)))
    shipping_per_kg = Decimal(str(getattr(settings, "SHIPPING_PER_KG", 0)))
    total_weight = Decimal("0.00")
    for item in cart.items.select_related("book").all():
        raw = (item.book.weight or "").strip()
        if raw:
            match = re.search(r"(\\d+(?:\\.\\d+)?)", raw)
            if match:
                try:
                    total_weight += Decimal(match.group(1)) * item.quantity
                except (InvalidOperation, ValueError, TypeError):
                    pass
    shipping_amount = shipping_base + (total_weight * shipping_per_kg)

    gst_rate = Decimal(str(getattr(settings, "GST_RATE", 0)))
    gst_amount = (subtotal - discount_amount) * gst_rate / Decimal("100") if gst_rate else Decimal("0.00")
    total_cost = subtotal - discount_amount + gst_amount + shipping_amount

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "shipping_amount": shipping_amount,
        "total_cost": total_cost,
    }


def _cart_category_ids(cart):
    return list(
        cart.items.select_related("book__category")
        .exclude(book__category__isnull=True)
        .values_list("book__category_id", flat=True)
        .distinct()
    )


def _validate_coupon_for_cart(raw_code, cart, subtotal):
    code = (raw_code or "").strip().upper()
    if not code:
        return None, ""

    coupon = Coupon.objects.filter(code__iexact=code).first()
    if not coupon:
        return None, "❌ Invalid coupon code."

    valid, message = coupon.validate_for_cart(
        subtotal=subtotal,
        category_ids=_cart_category_ids(cart),
    )
    if not valid:
        return None, message
    return coupon, "Coupon applied."


def _totals_with_coupon(base_totals, coupon):
    totals = dict(base_totals)
    coupon_discount = Decimal("0.00")
    if coupon:
        coupon_discount = coupon.discount_amount_for_subtotal(totals["subtotal"])
    combined_discount = totals["discount_amount"] + coupon_discount
    taxable = max(totals["subtotal"] - combined_discount, Decimal("0.00"))
    gst_amount = taxable * totals["gst_rate"] / Decimal("100") if totals["gst_rate"] else Decimal("0.00")
    totals["coupon_discount"] = coupon_discount
    totals["discount_amount"] = combined_discount
    totals["gst_amount"] = gst_amount
    totals["total_cost"] = taxable + totals["shipping_amount"] + gst_amount
    return totals


# ==================================================
# CHECKOUT + AUTO USER HANDLING
# ==================================================
def checkout(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        cart_id = request.session.get('cart_id')
        cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()

    if not cart or not (cart.items.exists() or cart.bundle_items.exists()):
        return redirect('cart_detail')

    stock_issues = _validate_cart_stock(cart)
    if stock_issues:
        messages.error(request, "Some items exceed stock: " + ", ".join(stock_issues[:3]))
        return redirect('cart_detail')

    addresses = []
    default_address = None
    if request.user.is_authenticated:
        addresses = list(UserAddress.objects.filter(user=request.user))
        default_address = next((addr for addr in addresses if addr.is_default), None)

    base_totals = _calculate_checkout_totals(cart)
    coupon_code = (request.GET.get("coupon_code") or "").strip()
    selected_coupon = None
    coupon_error = ""
    if coupon_code:
        selected_coupon, coupon_error = _validate_coupon_for_cart(coupon_code, cart, base_totals["subtotal"])
        if not selected_coupon and coupon_error:
            messages.error(request, f"{coupon_error}")
    totals = _totals_with_coupon(base_totals, selected_coupon)

    wallet = None
    max_redeemable = 0
    coin_settings = get_coin_settings()
    requested_redeem = 0
    estimated_earn = 0
    payable_total = totals["total_cost"]
    if request.user.is_authenticated:
        process_due_pending_rewards_for_user(request.user)
        wallet = get_wallet(request.user)
        max_redeemable = get_max_redeemable(wallet, totals["total_cost"])
        estimated_earn = estimate_purchase_coins(request.user, totals["total_cost"])
        try:
            requested_redeem = int(request.GET.get("redeem_coins") or 0)
        except (TypeError, ValueError):
            requested_redeem = 0
        requested_redeem = max(0, min(requested_redeem, max_redeemable))
        payable_total = totals["total_cost"] - Decimal(requested_redeem)
        if payable_total < 0:
            payable_total = Decimal("0.00")

    if request.method == "POST":
        messages.error(request, "Please complete payment to place the order.")
        return redirect("checkout")

    return render(request, "store/checkout.html", {
        'cart': cart,
        **totals,
        'addresses': addresses,
        'default_address': default_address,
        'razorpay_key_id': getattr(settings, "RAZORPAY_KEY_ID", ""),
        'razorpay_enabled': getattr(settings, "RAZORPAY_ENABLED", False),
        'selected_coupon': selected_coupon,
        'coupon_code': coupon_code,
        'coupon_error': coupon_error,
        'coin_wallet': wallet,
        'coin_max_redeemable': max_redeemable,
        'coin_settings': coin_settings,
        'requested_redeem': requested_redeem,
        'payable_total': payable_total,
    })


@require_POST
def razorpay_create_order(request):
    if not getattr(settings, "RAZORPAY_ENABLED", False):
        return JsonResponse({"ok": False, "error": "Razorpay is not configured."}, status=400)

    client = _get_razorpay_client()
    if not client:
        return JsonResponse({"ok": False, "error": "Razorpay client not available."}, status=400)

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        cart_id = request.session.get('cart_id')
        cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()

    if not cart or not (cart.items.exists() or cart.bundle_items.exists()):
        return JsonResponse({"ok": False, "error": "Cart is empty."}, status=400)

    stock_issues = _validate_cart_stock(cart)
    if stock_issues:
        return JsonResponse({"ok": False, "error": "Some items exceed stock: " + ", ".join(stock_issues[:3])}, status=400)

    full_name = (request.POST.get("full_name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    if not full_name or not email:
        return JsonResponse({"ok": False, "error": "Name and email are required."}, status=400)

    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        user, created = User.objects.get_or_create(email=email, defaults={"username": email})
        if created:
            password = get_random_string(10)
            user.set_password(password)
            user.save()
        cart.user = user
        cart.save(update_fields=["user"])
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    base_totals = _calculate_checkout_totals(cart)
    coupon_code = (request.POST.get("coupon_code") or "").strip()
    selected_coupon, coupon_error = _validate_coupon_for_cart(coupon_code, cart, base_totals["subtotal"])
    if coupon_code and not selected_coupon:
        return JsonResponse({"ok": False, "error": coupon_error}, status=400)
    totals = _totals_with_coupon(base_totals, selected_coupon)
    requested_redeem = 0
    estimated_earn = 0
    payable_total = totals["total_cost"]
    if user and user.is_authenticated:
        process_due_pending_rewards_for_user(user)
        wallet = get_wallet(user)
        max_redeemable = get_max_redeemable(wallet, totals["total_cost"])
        try:
            requested_redeem = int(request.POST.get("redeem_coins") or 0)
        except (TypeError, ValueError):
            requested_redeem = 0
        requested_redeem = max(0, min(requested_redeem, max_redeemable))
        estimated_earn = estimate_purchase_coins(user, totals["total_cost"])
        payable_total = totals["total_cost"] - Decimal(requested_redeem)
        if payable_total < 0:
            payable_total = Decimal("0.00")

    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            mobile=request.POST.get("mobile"),
            address=request.POST.get("address"),
            city=request.POST.get("city"),
            zip_code=request.POST.get("zip_code"),
            subtotal=totals["subtotal"],
            discount_amount=totals["discount_amount"],
            gst_rate=totals["gst_rate"],
            gst_amount=totals["gst_amount"],
            shipping_amount=totals["shipping_amount"],
            total_cost=payable_total,
            coupon=selected_coupon,
            status="Pending",
            is_paid=False,
            payment_method="razorpay",
            coins_redeemed=requested_redeem,
            coins_earned_estimate=estimated_earn,
            coins_earned_final=estimated_earn,
        )

        for item in cart.items.select_related("book").all():
            OrderItem.objects.create(
                order=order,
                book=item.book,
                price=item.book.price,
                quantity=item.quantity,
            )

        for bundle_item in cart.bundle_items.select_related("bundle").all():
            books = list(bundle_item.bundle.books.all())
            if not books:
                continue
            per_book_price = bundle_item.bundle.bundle_price / len(books)
            for book in books:
                OrderItem.objects.create(
                    order=order,
                    book=book,
                    price=per_book_price,
                    quantity=bundle_item.quantity,
                )

    if request.user.is_authenticated and request.POST.get("save_address"):
        label = request.POST.get("address_label", "Checkout").strip() or "Checkout"
        is_default = bool(request.POST.get("set_default"))
        if is_default:
            UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
        UserAddress.objects.create(
            user=request.user,
            label=label,
            full_name=full_name,
            phone=request.POST.get("mobile"),
            address=request.POST.get("address"),
            city=request.POST.get("city"),
            zip_code=request.POST.get("zip_code"),
            is_default=is_default,
        )

    amount_paise = int(payable_total * Decimal("100"))
    if amount_paise < 100:
        return JsonResponse(
            {
                "ok": False,
                "error": "Payable amount must be at least Rs. 1.00 to initiate online payment.",
            },
            status=400,
        )

    try:
        rz_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": f"order_{order.id}",
        })
    except Exception as exc:
        logger.exception("Failed to create Razorpay order")
        detail = str(exc).strip()
        if detail:
            message = f"Unable to initiate payment. {detail}"
        else:
            message = "Unable to initiate payment."
        return JsonResponse({"ok": False, "error": message}, status=500)

    order.razorpay_order_id = rz_order.get("id", "")
    order.save(update_fields=["razorpay_order_id"])

    return JsonResponse({
        "ok": True,
        "razorpay_key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
        "razorpay_order_id": order.razorpay_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "order_id": order.id,
        "name": "Idara Kitab Ul Shifa",
        "prefill": {
            "name": full_name,
            "email": email,
            "contact": request.POST.get("mobile", ""),
        },
    })


@require_POST
def razorpay_verify_payment(request):
    if not getattr(settings, "RAZORPAY_ENABLED", False):
        return JsonResponse({"ok": False, "error": "Razorpay is not configured."}, status=400)

    client = _get_razorpay_client()
    if not client:
        return JsonResponse({"ok": False, "error": "Razorpay client not available."}, status=400)

    order_id = request.POST.get("order_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    if not all([order_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse({"ok": False, "error": "Missing payment details."}, status=400)

    order = get_object_or_404(Order, id=order_id, razorpay_order_id=razorpay_order_id)

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except Exception:
        return JsonResponse({"ok": False, "error": "Payment verification failed."}, status=400)

    order.is_paid = True
    order.status = "Processing"
    order.razorpay_payment_id = razorpay_payment_id
    order.razorpay_signature = razorpay_signature
    order.save(update_fields=["is_paid", "status", "razorpay_payment_id", "razorpay_signature"])
    apply_redemption_for_order(order)

    partial_backorder = []
    for item in order.items.select_related("book").all():
        available = max(item.book.stock, 0)
        allocated = min(item.quantity, available)
        backordered = max(item.quantity - allocated, 0)
        if allocated:
            item.book.stock -= allocated
            item.book.save(update_fields=["stock"])
        item.allocated_quantity = allocated
        item.backordered_quantity = backordered
        item.save(update_fields=["allocated_quantity", "backordered_quantity"])
        if backordered:
            partial_backorder.append(f"{item.book.title} ({backordered})")

    if partial_backorder:
        order.sub_status = "Partially allocated, waiting for stock"
        order.internal_comment = (
            "Partial allocation at payment: " + ", ".join(partial_backorder[:6])
        )
        order.save(update_fields=["sub_status", "internal_comment"])

    if order.user_id:
        cart = Cart.objects.filter(user_id=order.user_id).first()
        if cart:
            cart.items.all().delete()
            cart.bundle_items.all().delete()
    else:
        if 'cart_id' in request.session:
            del request.session['cart_id']

    enqueue_order_confirmation(order.id)
    enqueue_order_alert(order.id)
    if order.user_id:
        process_due_pending_rewards_for_user(order.user)

    token = signing.dumps({"order_id": order.id, "email": order.email})
    success_url = reverse("order_success", args=[order.id]) + f"?token={token}"

    return JsonResponse({"ok": True, "redirect_url": success_url})


def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    token = request.GET.get("token")

    if request.user.is_authenticated:
        if not (request.user.is_staff or order.user_id == request.user.id):
            return redirect("home")
    else:
        if not token:
            return redirect("home")
        try:
            data = signing.loads(token, max_age=60 * 60 * 24 * 7)
        except Exception:
            return redirect("home")
        if data.get("order_id") != order.id or data.get("email") != order.email:
            return redirect("home")

    invoice_token = signing.dumps({"order_id": order.id, "email": order.email})
    return render(request, "store/order_success.html", {
        "order": order,
        "invoice_token": invoice_token,
    })
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

def publish_with_us(request):
    if request.method == "POST":
        payload = {k: request.POST.get(k, "").strip() for k in request.POST.keys()}
        if payload.get("title") and payload.get("author_name"):
            PublishWithUsSubmission.objects.create(
                title=payload.get("title", ""),
                subtitle=payload.get("subtitle", ""),
                author_name=payload.get("author_name", ""),
                position_affiliation=payload.get("position_affiliation", ""),
                mailing_address=payload.get("mailing_address", ""),
                phone=payload.get("phone", ""),
                email=payload.get("email", ""),
                topic_definition=payload.get("topic_definition", ""),
                overview=payload.get("overview", ""),
                reasons=payload.get("reasons", ""),
                unique_features=payload.get("unique_features", ""),
                competition=payload.get("competition", ""),
                toc=payload.get("toc", ""),
                pages=payload.get("pages", ""),
                delivery_time=payload.get("delivery_time", ""),
                text_electronic=payload.get("text_electronic", ""),
                text_software=payload.get("text_software", ""),
                special_features=payload.get("special_features", ""),
                figures_computer=payload.get("figures_computer", ""),
                figures_software=payload.get("figures_software", ""),
                market=payload.get("market", ""),
                societies=payload.get("societies", ""),
                journals=payload.get("journals", ""),
                textbook_details=payload.get("textbook_details", ""),
                previous_works=payload.get("previous_works", ""),
                why_better=payload.get("why_better", ""),
                reviewers=payload.get("reviewers", ""),
            )
        subject = f"New Book Proposal: {payload.get('title') or 'Untitled'}"
        html_body = render_to_string("emails/publish_with_us.html", {"data": payload})
        text_body = strip_tags(html_body)
        try:
            send_publish_with_us(subject, text_body, html_body)
            messages.success(request, "Thank you! Your proposal has been submitted.")
        except Exception as exc:
            logger.exception("Publish With Us submission failed: %s", exc)
            messages.error(request, "Something went wrong. Please try again.")

    return render(request, 'store/publish_with_us.html')


def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    token = request.GET.get("token")

    if request.user.is_authenticated:
        if not (request.user.is_staff or order.user_id == request.user.id):
            return redirect("home")
    else:
        if not token:
            return redirect("home")
        try:
            data = signing.loads(token, max_age=60 * 60 * 24 * 7)
        except Exception:
            return redirect("home")
        if data.get("order_id") != order.id or data.get("email") != order.email:
            return redirect("home")

    return render(request, "store/invoice.html", {"order": order})

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
