from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0022_sitesettings_loader_logo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banner",
            name="mobile_height",
            field=models.PositiveSmallIntegerField(
                default=360,
                help_text="Banner height in pixels for mobile screens.",
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="tablet_height",
            field=models.PositiveSmallIntegerField(
                default=420,
                help_text="Banner height in pixels for tablet screens.",
            ),
        ),
    ]
