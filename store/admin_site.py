import json
from datetime import timedelta

from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone

from .models import Book, Order, OrderItem


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

        best_sellers = (
            OrderItem.objects.filter(order__is_paid=True)
            .values("book__title")
            .annotate(qty=Sum("quantity"))
            .order_by("-qty")[:8]
        )

        low_stock = Book.objects.filter(stock__lte=5).order_by("stock", "title")[:10]

        total_sales = (
            Order.objects.filter(is_paid=True).aggregate(total=Sum("total_cost"))["total"] or 0
        )
        total_orders = Order.objects.filter(is_paid=True).count()
        today_orders = Order.objects.filter(is_paid=True, created_at__date=today).count()

        extra_context.update({
            "day_labels": json.dumps([d.strftime("%b %d") for d in day_labels]),
            "day_series": json.dumps(day_series),
            "month_labels": json.dumps([d.strftime("%b %Y") for d in month_labels]),
            "month_series": json.dumps(month_series),
            "best_sellers": best_sellers,
            "low_stock": low_stock,
            "total_sales": total_sales,
            "total_orders": total_orders,
            "today_orders": today_orders,
        })

        return super().index(request, extra_context=extra_context)
