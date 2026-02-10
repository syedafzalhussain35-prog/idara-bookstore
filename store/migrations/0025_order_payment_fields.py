from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0024_sitesettings_sales_offers"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(default="razorpay", max_length=30),
        ),
        migrations.AddField(
            model_name="order",
            name="razorpay_order_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="razorpay_payment_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="razorpay_signature",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
