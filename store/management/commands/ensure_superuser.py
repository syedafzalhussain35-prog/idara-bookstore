import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser if it does not exist (uses env vars)."

    def handle(self, *args, **options):
        username = os.getenv("SUPERUSER_USERNAME")
        email = os.getenv("SUPERUSER_EMAIL")
        password = os.getenv("SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write("SUPERUSER_USERNAME or SUPERUSER_PASSWORD not set; skipping.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write("Superuser already exists; skipping.")
            return

        user = User.objects.create_superuser(
            username=username,
            email=email or "",
            password=password,
        )
        self.stdout.write(f"Superuser created: {user.username}")
