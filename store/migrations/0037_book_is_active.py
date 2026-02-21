from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0036_banner_desktop_crop_height_banner_desktop_crop_width_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
