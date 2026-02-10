from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0023_banner_height_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="sales_offers_label",
            field=models.CharField(default="Sales/Offers", max_length=40),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="sales_offers_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
