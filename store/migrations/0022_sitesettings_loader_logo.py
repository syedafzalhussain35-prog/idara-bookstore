from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0021_sitesettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="loader_logo",
            field=models.ImageField(blank=True, null=True, upload_to="site/"),
        ),
    ]
