from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0019_rename_store_audi_action_ba4b6f_idx_store_audit_action_1ee354_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="isbn",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="book",
            name="published_year",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="book",
            name="binding",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="book",
            name="pages",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="book",
            name="weight",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="book",
            name="readership",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="book",
            name="toc_pdf",
            field=models.FileField(blank=True, null=True, upload_to="books/pdfs/"),
        ),
        migrations.AddField(
            model_name="book",
            name="sample_pdf",
            field=models.FileField(blank=True, null=True, upload_to="books/pdfs/"),
        ),
    ]
