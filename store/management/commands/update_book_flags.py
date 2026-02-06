from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from store.models import Book, OrderItem


class Command(BaseCommand):
    help = "Update bestseller and trending flags based on recent sales."

    def handle(self, *args, **options):
        min_sales = getattr(settings, "BESTSELLER_MIN_SALES", 15)
        trending_days = getattr(settings, "TRENDING_DAYS", 7)

        bestseller_ids = list(
            OrderItem.objects
            .values_list("book_id", flat=True)
            .annotate(total=Sum("quantity"))
            .filter(total__gte=min_sales)
        )

        Book.objects.update(is_bestseller=False)
        if bestseller_ids:
            Book.objects.filter(id__in=bestseller_ids).update(is_bestseller=True)

        since = timezone.now() - timedelta(days=trending_days)
        trending_ids = list(
            OrderItem.objects
            .filter(order__created_at__gte=since)
            .values_list("book_id", flat=True)
            .annotate(total=Sum("quantity"))
            .order_by("-total")[:20]
        )

        Book.objects.update(is_trending=False)
        if trending_ids:
            Book.objects.filter(id__in=trending_ids).update(is_trending=True)

        self.stdout.write(self.style.SUCCESS("Book flags updated."))
