from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0029_catalogue"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BOM",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("bom_code", models.CharField(blank=True, max_length=30)),
                ("sku_code", models.CharField(max_length=100)),
                ("product_name", models.CharField(blank=True, default="", max_length=150)),
                ("catalogue_name", models.CharField(blank=True, default="", max_length=120)),
                ("gender", models.CharField(blank=True, choices=[("male", "Male"), ("female", "Female"), ("unisex", "Unisex"), ("kids", "Kids")], default="unisex", max_length=20)),
                ("size_type", models.CharField(choices=[("character", "Character"), ("numeric", "Numeric"), ("alpha", "Alpha"), ("free", "Free Size")], default="character", max_length=20)),
                ("sub_category", models.CharField(blank=True, default="", max_length=120)),
                ("character_name", models.CharField(blank=True, default="", max_length=120)),
                ("license_name", models.CharField(blank=True, default="", max_length=120)),
                ("color_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("accessories_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("maintenance_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("selling_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("booked_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("available_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("damage_percent", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("is_discontinued", models.BooleanField(default=False)),
                ("product_image", models.ImageField(blank=True, null=True, upload_to="bom/%Y/%m/")),
                ("size_chart_image", models.ImageField(blank=True, null=True, upload_to="bom/%Y/%m/")),
                ("notes", models.TextField(blank=True, default="")),
                ("brand", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="boms", to="accounts.brand")),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="boms", to="accounts.category")),
                ("main_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="boms", to="accounts.maincategory")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("pattern_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="boms", to="accounts.patterntype")),
            ],
            options={
                "ordering": ["-id"],
                "unique_together": {("owner", "bom_code"), ("owner", "sku_code")},
            },
        ),
        migrations.CreateModel(
            name="BOMExpenseItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expense_name", models.CharField(max_length=120)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("bom", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expense_items", to="accounts.bom")),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="BOMJobberItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("bom", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jobber_items", to="accounts.bom")),
                ("jobber", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bom_jobber_items", to="accounts.jobber")),
                ("jobber_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bom_jobber_items", to="accounts.jobbertype")),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="BOMMaterialItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_type", models.CharField(choices=[("raw_fabric", "Raw Fabric"), ("accessory", "Accessory"), ("trim", "Trim"), ("packing", "Packing"), ("other", "Other")], default="raw_fabric", max_length=20)),
                ("cost_per_uom", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("average", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("cost", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("bom", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="material_items", to="accounts.bom")),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bom_material_items", to="accounts.material")),
                ("unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bom_material_items", to="accounts.materialunit")),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="BOMProcessItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("bom", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="process_items", to="accounts.bom")),
                ("jobber_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bom_process_items", to="accounts.jobbertype")),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
    ]