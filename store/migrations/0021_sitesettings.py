from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0020_book_specs_and_files"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("background_image", models.ImageField(blank=True, null=True, upload_to="site/")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
