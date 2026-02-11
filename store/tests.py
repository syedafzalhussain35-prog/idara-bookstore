from decimal import Decimal

from django.contrib.auth.models import AnonymousUser, User
from django.template.loader import get_template
from django.test import TestCase

from .models import Book, Review
from .views import _apply_price_rating_filters, _to_decimal


class FilterHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="x")
        self.book_high = Book.objects.create(title="High", author="A", price=Decimal("500.00"), stock=5)
        self.book_low = Book.objects.create(title="Low", author="B", price=Decimal("150.00"), stock=5)
        Review.objects.create(user=self.user, book=self.book_high, rating=5, comment="great")
        Review.objects.create(user=self.user, book=self.book_low, rating=2, comment="ok")

    def test_to_decimal_parses_valid_and_invalid(self):
        self.assertEqual(_to_decimal("99.5"), Decimal("99.5"))
        self.assertIsNone(_to_decimal(""))
        self.assertIsNone(_to_decimal("abc"))

    def test_apply_price_filters(self):
        qs = _apply_price_rating_filters(Book.objects.all(), min_price_raw="200", max_price_raw="600")
        self.assertQuerySetEqual(qs.order_by("id"), [self.book_high], transform=lambda b: b)

    def test_apply_rating_filter(self):
        qs = _apply_price_rating_filters(Book.objects.all(), rating_raw="4")
        self.assertQuerySetEqual(qs.order_by("id"), [self.book_high], transform=lambda b: b)

    def test_invalid_inputs_do_not_crash_or_filter(self):
        qs = _apply_price_rating_filters(Book.objects.all(), min_price_raw="bad", max_price_raw="nope", rating_raw="nanx")
        self.assertEqual(qs.count(), 2)


class MobileHeaderRenderTests(TestCase):
    def setUp(self):
        self.template = get_template("store/base.html")
        self.book = Book.objects.create(title="Recent Book", author="R", price=Decimal("199.00"), stock=3)
        self.staff_user = User.objects.create_user(username="adminuser", password="x", is_staff=True)

    def _render(self, user, recently_viewed_books=None):
        context = {
            "user": user,
            "request": type("Req", (), {"path": "/"})(),
            "recently_viewed_books": recently_viewed_books or [],
            "cart_count": 0,
            "cart_preview_total": Decimal("0.00"),
            "cart_preview_items": [],
            "wishlist_count": 0,
            "wishlist_preview_items": [],
            "nav_categories": [],
            "sales_offers_enabled": False,
            "site_background_url": "",
            "site_loader_logo": "",
        }
        return self.template.render(context)

    def test_staff_mobile_admin_link_present(self):
        html = self._render(self.staff_user, recently_viewed_books=[self.book])
        self.assertIn('class="mobile-admin-link"', html)
        self.assertIn('data-mobile-href="/wishlist/"', html)
        self.assertIn('data-mobile-href="/cart/"', html)
        self.assertIn("window.location.href = mobileHref;", html)

    def test_anonymous_login_mobile_target_present(self):
        html = self._render(AnonymousUser())
        self.assertIn('data-mobile-href="/accounts/login/?next=/"', html)
