import json
from datetime import timedelta

from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.conf import settings

from .models import (
    Banner,
    Book,
    Bundle,
    Category,
    Coupon,
    Order,
    OrderItem,
    PublishWithUsSubmission,
    SiteSettings,
    Subject,
)


class IdaraAdminSite(AdminSite):
    site_header = "Idara Seller Center"
    site_title = "Idara Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        today = timezone.localdate()
        start_day = today - timedelta(days=13)

        sales_by_day_qs = (
            Order.objects.filter(is_paid=True, created_at__date__gte=start_day)
            .annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(total=Sum("total_cost"))
            .order_by("day")
        )
        day_totals = {row["day"].date(): float(row["total"] or 0) for row in sales_by_day_qs}
        day_labels = [start_day + timedelta(days=i) for i in range(14)]
        day_series = [day_totals.get(d, 0) for d in day_labels]

        start_month = today.replace(day=1)
        month_labels = []
        for i in range(11, -1, -1):
            month = (start_month.month - i - 1) % 12 + 1
            year = start_month.year + (start_month.month - i - 1) // 12
            month_labels.append(timezone.datetime(year, month, 1).date())

        sales_by_month_qs = (
            Order.objects.filter(is_paid=True, created_at__date__gte=month_labels[0])
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("total_cost"))
            .order_by("month")
        )
        month_totals = {row["month"].date(): float(row["total"] or 0) for row in sales_by_month_qs}
        month_series = [month_totals.get(d, 0) for d in month_labels]

        best_sellers_qs = (
            OrderItem.objects.filter(order__is_paid=True)
            .values("book__title")
            .annotate(qty=Sum("quantity"))
            .order_by("-qty")[:8]
        )
        best_sellers = list(best_sellers_qs)

        low_stock = Book.objects.filter(stock__lte=5).order_by("stock", "title")[:10]
        low_stock_total = Book.objects.filter(stock__lte=5).count()
        low_stock_critical = Book.objects.filter(stock__lte=2).count()

        total_sales = Order.objects.filter(is_paid=True).aggregate(total=Sum("total_cost"))["total"] or 0
        total_orders_all = Order.objects.count()
        paid_orders = Order.objects.filter(is_paid=True).count()
        today_orders = Order.objects.filter(created_at__date=today).count()
        pending_orders = Order.objects.filter(status="Pending").count()
        processing_orders = Order.objects.filter(status__in=["Processing", "Packed", "Shipped"]).count()
        unpaid_orders = Order.objects.filter(is_paid=False).count()

        categories_total = Category.objects.count()
        subjects_total = Subject.objects.count()
        banners_total = Banner.objects.count()
        active_banners = Banner.objects.filter(is_active=True).count()
        bundles_total = Bundle.objects.count()

        active_coupons = Coupon.objects.filter(active=True).count()
        soon_cutoff = today + timedelta(days=7)
        expiring_coupons = Coupon.objects.filter(active=True, expiry_date__isnull=False, expiry_date__lte=soon_cutoff).count()

        submissions_total = PublishWithUsSubmission.objects.count()
        recent_submissions = PublishWithUsSubmission.objects.order_by("-created_at")[:5]

        books_without_cover = Book.objects.filter(main_cover="").count() + Book.objects.filter(main_cover__isnull=True).count()
        books_without_category = Book.objects.filter(category__isnull=True).count()

        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:8]

        settings_obj = SiteSettings.objects.filter(is_active=True).first()
        razorpay_enabled = bool(getattr(settings, "RAZORPAY_KEY_ID", "") and getattr(settings, "RAZORPAY_KEY_SECRET", ""))
        key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
        razorpay_key_mask = f"****{key_id[-6:]}" if key_id else ""

        extra_context.update({
            "day_labels": json.dumps([d.strftime("%b %d") for d in day_labels]),
            "day_series": json.dumps(day_series),
            "month_labels": json.dumps([d.strftime("%b %Y") for d in month_labels]),
            "month_series": json.dumps(month_series),
            "best_sellers": best_sellers,
            "best_sellers_count": len(best_sellers),
            "low_stock": low_stock,
            "low_stock_total": low_stock_total,
            "low_stock_critical": low_stock_critical,
            "total_sales": total_sales,
            "total_orders_all": total_orders_all,
            "paid_orders": paid_orders,
            "today_orders": today_orders,
            "pending_orders": pending_orders,
            "processing_orders": processing_orders,
            "unpaid_orders": unpaid_orders,
            "categories_total": categories_total,
            "subjects_total": subjects_total,
            "banners_total": banners_total,
            "active_banners": active_banners,
            "bundles_total": bundles_total,
            "active_coupons": active_coupons,
            "expiring_coupons": expiring_coupons,
            "submissions_total": submissions_total,
            "recent_submissions": recent_submissions,
            "books_without_cover": books_without_cover,
            "books_without_category": books_without_category,
            "recent_orders": recent_orders,
            "settings_obj": settings_obj,
            "razorpay_enabled": razorpay_enabled,
            "razorpay_key_mask": razorpay_key_mask,
        })

        return super().index(request, extra_context=extra_context)
