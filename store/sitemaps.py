from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Book, Category, Subject, UnaniTerm


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "home",
            "about",
            "contact",
            "gallery",
            "offers",
            "publish_with_us",
            "dictionary_list",
            "unani_weight_converter",
        ]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    priority = 0.8
    changefreq = "daily"

    def items(self):
        return Category.objects.all().only("slug")

    def location(self, obj):
        return reverse("category_books", args=[obj.slug])


class SubjectSitemap(Sitemap):
    priority = 0.8
    changefreq = "daily"

    def items(self):
        return Subject.objects.filter(is_active=True).only("slug")

    def location(self, obj):
        return reverse("subject_books", args=[obj.slug])


class BookSitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Book.objects.filter(stock__gt=0).only("id", "created_at")

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse("book_detail", args=[obj.id])


class DictionarySitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return UnaniTerm.objects.filter(is_published=True).only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("dictionary_detail", args=[obj.slug])
