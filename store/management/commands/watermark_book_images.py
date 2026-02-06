from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from store.models import Book, BookImage, _apply_text_watermark


class Command(BaseCommand):
    help = "Apply watermark to existing book cover and gallery images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many images would be processed without modifying files.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of images processed (0 = no limit).",
        )
        parser.add_argument(
            "--covers-only",
            action="store_true",
            help="Only watermark book main covers.",
        )
        parser.add_argument(
            "--gallery-only",
            action="store_true",
            help="Only watermark book gallery images.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"] or 0
        covers_only = options["covers_only"]
        gallery_only = options["gallery_only"]

        if covers_only and gallery_only:
            self.stdout.write(self.style.ERROR("Choose only one of --covers-only or --gallery-only."))
            return

        if not getattr(settings, "BOOK_WATERMARK_ENABLED", True):
            self.stdout.write(self.style.WARNING("BOOK_WATERMARK_ENABLED is false. Nothing to do."))
            return

        watermark_text = getattr(settings, "BOOK_WATERMARK_TEXT", "Idara")

        cover_qs = Book.objects.filter(main_cover__isnull=False, is_watermarked=False)
        gallery_qs = BookImage.objects.filter(image__isnull=False, is_watermarked=False)

        if covers_only:
            gallery_qs = BookImage.objects.none()
        if gallery_only:
            cover_qs = Book.objects.none()

        cover_ids = list(cover_qs.values_list("id", flat=True))
        gallery_ids = list(gallery_qs.values_list("id", flat=True))

        total = len(cover_ids) + len(gallery_ids)
        if limit:
            remaining = limit
            cover_ids = cover_ids[:remaining]
            remaining = max(0, remaining - len(cover_ids))
            gallery_ids = gallery_ids[:remaining]

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would watermark {len(cover_ids)} covers and {len(gallery_ids)} gallery images."))
            return

        updated = 0
        with transaction.atomic():
            for book in Book.objects.filter(id__in=cover_ids):
                if _apply_text_watermark(book.main_cover, watermark_text):
                    book.is_watermarked = True
                    book.save(update_fields=["is_watermarked"])
                    updated += 1

            for image in BookImage.objects.filter(id__in=gallery_ids):
                if _apply_text_watermark(image.image, watermark_text):
                    image.is_watermarked = True
                    image.save(update_fields=["is_watermarked"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Watermarked {updated} images."))
