from django.apps import AppConfig
import os


class StoreConfig(AppConfig):
    name = 'store'

    def ready(self):
        admin_user = os.getenv('ADMIN_USER')
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_pass = os.getenv('ADMIN_PASS')

        if not admin_user or not admin_pass:
            return

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if not User.objects.filter(username=admin_user).exists():
                User.objects.create_superuser(
                    username=admin_user,
                    email=admin_email or '',
                    password=admin_pass,
                )
        except Exception:
            # DB might not be ready during startup; skip silently.
            return
