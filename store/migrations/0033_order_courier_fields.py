from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0032_classicalweightunit"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="consignment_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Tracking/consignment number shared with customer.",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="courier_service",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not set"),
                    ("india_post", "India Post"),
                    ("delhivery", "Delhivery"),
                    ("dtdc", "DTDC"),
                    ("bluedart", "Blue Dart"),
                    ("other", "Other"),
                ],
                default="",
                help_text="Select the courier used for this shipment.",
                max_length=30,
            ),
        ),
    ]
