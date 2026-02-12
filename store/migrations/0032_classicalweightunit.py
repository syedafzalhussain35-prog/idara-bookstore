from decimal import Decimal

from django.db import migrations, models
import django.core.validators


def seed_classical_weight_units(apps, schema_editor):
    ClassicalWeightUnit = apps.get_model("store", "ClassicalWeightUnit")
    default_source = "Traditional Knowledge Resource Classification code, NISCAIR; NFUM"
    rows = [
        ("1 Chana", "170mg", Decimal("0.170000"), 1),
        ("1 Chawal", "15mg", Decimal("0.015000"), 2),
        ("1 Chatank", "60gm", Decimal("60.000000"), 3),
        ("1 Daang", "500mg", Decimal("0.500000"), 4),
        ("1 Dam", "21g", Decimal("21.000000"), 5),
        ("1 Dirham", "3.5gm", Decimal("3.500000"), 6),
        ("1 Gehun", "46.6mg", Decimal("0.046600"), 7),
        ("1 Jau", "60mg", Decimal("0.060000"), 8),
        ("1 Khurma", "5g", Decimal("5.000000"), 9),
        ("1 Masha", "1g", Decimal("1.000000"), 10),
        ("1 Misqal", "4.5g", Decimal("4.500000"), 11),
        ("1 Moong", "42mg", Decimal("0.042000"), 12),
        ("Pao", "240gm", Decimal("240.000000"), 13),
        ("1 Ratti", "125mg", Decimal("0.125000"), 14),
        ("Ser", "960gm", Decimal("960.000000"), 15),
        ("1 Tola", "12g", Decimal("12.000000"), 16),
    ]
    for classical_weight, metric_weight, grams_value, display_order in rows:
        ClassicalWeightUnit.objects.update_or_create(
            classical_weight=classical_weight,
            defaults={
                "metric_weight": metric_weight,
                "grams_value": grams_value,
                "display_order": display_order,
                "is_active": True,
                "source_note": default_source,
            },
        )


def unseed_classical_weight_units(apps, schema_editor):
    ClassicalWeightUnit = apps.get_model("store", "ClassicalWeightUnit")
    names = [
        "1 Chana",
        "1 Chawal",
        "1 Chatank",
        "1 Daang",
        "1 Dam",
        "1 Dirham",
        "1 Gehun",
        "1 Jau",
        "1 Khurma",
        "1 Masha",
        "1 Misqal",
        "1 Moong",
        "Pao",
        "1 Ratti",
        "Ser",
        "1 Tola",
    ]
    ClassicalWeightUnit.objects.filter(classical_weight__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0031_unaniterm_table_structure"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassicalWeightUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("classical_weight", models.CharField(max_length=100, unique=True)),
                ("metric_weight", models.CharField(help_text="Example: 170mg, 3.5gm", max_length=50)),
                (
                    "grams_value",
                    models.DecimalField(
                        decimal_places=6,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.000001"))],
                    ),
                ),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("source_note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Classical Weight Unit",
                "verbose_name_plural": "Classical Weight Units",
                "ordering": ["display_order", "id"],
            },
        ),
        migrations.RunPython(seed_classical_weight_units, unseed_classical_weight_units),
    ]
