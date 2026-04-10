from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser, User
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import UnaniTermAdmin
from .models import Book, Order, OrderItem, Review, UnaniReferenceSource, UnaniTerm
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


class CheckoutSecurityTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(title="Secure Book", author="Author", price=Decimal("250.00"), stock=10)
        self.existing_user = User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="pass12345",
        )

    def test_add_to_cart_rejects_get(self):
        response = self.client.get(reverse("add_to_cart", args=[self.book.id]))
        self.assertEqual(response.status_code, 405)

    @patch("store.views._get_razorpay_client")
    @override_settings(RAZORPAY_ENABLED=True, RAZORPAY_KEY_ID="key", RAZORPAY_KEY_SECRET="secret")
    def test_guest_razorpay_create_order_does_not_login_existing_user(self, mock_client_factory):
        mock_client = Mock()
        mock_client.order.create.return_value = {"id": "order_test_1"}
        mock_client_factory.return_value = mock_client

        self.client.post(reverse("add_to_cart", args=[self.book.id]))
        response = self.client.post(
            reverse("razorpay_create_order"),
            data={
                "full_name": "Guest User",
                "email": "existing@example.com",
                "mobile": "9876543210",
                "address": "Street 1",
                "city": "Delhi",
                "zip_code": "110001",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        order = Order.objects.latest("id")
        self.assertIsNone(order.user)

    @patch("store.views._get_razorpay_client")
    @override_settings(RAZORPAY_ENABLED=True, RAZORPAY_KEY_ID="key", RAZORPAY_KEY_SECRET="secret")
    def test_razorpay_verify_payment_is_idempotent(self, mock_client_factory):
        mock_client = Mock()
        mock_client.utility.verify_payment_signature.return_value = None
        mock_client_factory.return_value = mock_client

        order = Order.objects.create(
            full_name="Test Buyer",
            email="buyer@example.com",
            mobile="9876543210",
            address="Address",
            city="Delhi",
            zip_code="110001",
            subtotal=Decimal("250.00"),
            total_cost=Decimal("250.00"),
            razorpay_order_id="rzp_order_123",
            status="Pending",
            is_paid=False,
        )
        OrderItem.objects.create(order=order, book=self.book, price=self.book.price, quantity=2)

        payload = {
            "order_id": str(order.id),
            "razorpay_order_id": "rzp_order_123",
            "razorpay_payment_id": "rzp_pay_123",
            "razorpay_signature": "sig_123",
        }

        first = self.client.post(reverse("razorpay_verify_payment"), data=payload)
        self.assertEqual(first.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 8)

        second = self.client.post(reverse("razorpay_verify_payment"), data=payload)
        self.assertEqual(second.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 8)


class DictionaryListTests(TestCase):
    def setUp(self):
        self.reference = UnaniReferenceSource.objects.create(
            name="WHO international standard terminologies on Unani medicine"
        )
        self.term_a = UnaniTerm.objects.create(
            english_term="Term A",
            description="Desc A",
            section="Anatomy",
            reference_source=self.reference,
        )
        self.term_b = UnaniTerm.objects.create(
            english_term="Term B",
            description="Desc B",
            section=" Anatomy ",
            reference_source=self.reference,
        )
        self.term_blank = UnaniTerm.objects.create(
            english_term="Term Blank",
            description="Desc Blank",
            section="   ",
            reference_source=self.reference,
        )

    def test_sections_are_trimmed_and_deduplicated(self):
        response = self.client.get(reverse("dictionary_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sections"], ["Anatomy"])

    def test_section_filter_matches_trimmed_section_values(self):
        response = self.client.get(reverse("dictionary_list"), {"section": "Anatomy"})
        self.assertEqual(response.status_code, 200)
        names = {term.english_term for term in response.context["page_obj"].object_list}
        self.assertIn("Term A", names)
        self.assertIn("Term B", names)
        self.assertNotIn("Term Blank", names)

    def test_reference_hidden_in_list_but_visible_in_detail(self):
        list_response = self.client.get(reverse("dictionary_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, 'class="term-reference"', status_code=200)

        detail_response = self.client.get(reverse("dictionary_detail", args=[self.term_a.slug]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Reference", status_code=200)
        self.assertContains(detail_response, self.reference.name, status_code=200)


class UnaniImportRobustnessTests(TestCase):
    def setUp(self):
        self.model_admin = UnaniTermAdmin(UnaniTerm, admin.site)
        self.existing = UnaniTerm.objects.create(
            english_term="Existing",
            description="Existing entry",
            slug="abnormal-temperament",
            transliteration="Existing",
        )

    def test_import_row_allows_slash_transliteration(self):
        status = self.model_admin.import_row(
            {
                "english_term": "Acute Stage",
                "description": "desc",
                "transliteration": "Hararat / Hiddat",
                "slug": "acute-stage",
            }
        )
        self.assertEqual(status, "created")
        term = UnaniTerm.objects.get(english_term="Acute Stage")
        self.assertEqual(term.transliteration, "Hararat / Hiddat")

    def test_import_row_autofixes_duplicate_slug(self):
        status = self.model_admin.import_row(
            {
                "english_term": "Abnormal Temperament Variant",
                "description": "desc",
                "transliteration": "Mizaj / Variant",
                "slug": "abnormal-temperament",
            }
        )
        self.assertEqual(status, "created")
        term = UnaniTerm.objects.get(english_term="Abnormal Temperament Variant")
        self.assertNotEqual(term.slug, "abnormal-temperament")
        self.assertTrue(term.slug.startswith("abnormal-temperament-"))
