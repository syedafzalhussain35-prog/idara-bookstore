from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0017_book_is_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='is_trending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='book',
            name='is_watermarked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='bookimage',
            name='is_watermarked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='gst_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='order',
            name='gst_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='UserAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(default='Home', max_length=100)),
                ('full_name', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('address', models.TextField()),
                ('city', models.CharField(max_length=100)),
                ('zip_code', models.CharField(max_length=10)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to='auth.user')),
            ],
            options={
                'ordering': ['-is_default', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SearchQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(db_index=True, max_length=255)),
                ('category_slug', models.CharField(blank=True, max_length=120)),
                ('subject_slug', models.CharField(blank=True, max_length=120)),
                ('min_price', models.CharField(blank=True, max_length=30)),
                ('max_price', models.CharField(blank=True, max_length=30)),
                ('rating', models.CharField(blank=True, max_length=30)),
                ('results_count', models.PositiveIntegerField(default=0)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('book_price_change', 'Book price change'), ('book_stock_change', 'Book stock change'), ('order_paid_change', 'Order paid change'), ('order_status_change', 'Order status change'), ('order_update', 'Order update')], max_length=50)),
                ('model_name', models.CharField(max_length=50)),
                ('object_id', models.PositiveIntegerField()),
                ('object_repr', models.CharField(blank=True, max_length=200)),
                ('changes', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='searchquerylog',
            index=models.Index(fields=['created_at'], name='store_searc_created_3c2f66_idx'),
        ),
        migrations.AddIndex(
            model_name='searchquerylog',
            index=models.Index(fields=['results_count'], name='store_searc_results_7d0c11_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action'], name='store_audi_action_ba4b6f_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['created_at'], name='store_audi_created_1edc8e_idx'),
        ),
    ]
