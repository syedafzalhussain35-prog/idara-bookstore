from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0030_unaniterm'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='unaniterm',
            name='store_unani_term_afc983_idx',
        ),
        migrations.RemoveIndex(
            model_name='unaniterm',
            name='store_unani_categor_77b204_idx',
        ),
        migrations.RenameField(
            model_name='unaniterm',
            old_name='term',
            new_name='english_term',
        ),
        migrations.RenameField(
            model_name='unaniterm',
            old_name='unani_explanation',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='unaniterm',
            old_name='arabic_term',
            new_name='arabic_script',
        ),
        migrations.RenameField(
            model_name='unaniterm',
            old_name='urdu_term',
            new_name='transliteration',
        ),
        migrations.RenameField(
            model_name='unaniterm',
            old_name='category',
            new_name='section',
        ),
        migrations.RemoveField(
            model_name='unaniterm',
            name='english_meaning',
        ),
        migrations.RemoveField(
            model_name='unaniterm',
            name='modern_medical_equivalent',
        ),
        migrations.AlterField(
            model_name='unaniterm',
            name='section',
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AlterModelOptions(
            name='unaniterm',
            options={'ordering': ['english_term']},
        ),
        migrations.AddIndex(
            model_name='unaniterm',
            index=models.Index(fields=['english_term'], name='store_unani_english_5ae955_idx'),
        ),
        migrations.AddIndex(
            model_name='unaniterm',
            index=models.Index(fields=['section', 'is_published'], name='store_unani_section_8b9016_idx'),
        ),
    ]
