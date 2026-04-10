from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_material_units(apps, schema_editor):
    MaterialUnit = apps.get_model("accounts", "MaterialUnit")
    YarnPurchaseOrderItem = apps.get_model("accounts", "YarnPurchaseOrderItem")
    GreigePurchaseOrderItem = apps.get_model("accounts", "GreigePurchaseOrderItem")
    DyeingPurchaseOrderItem = apps.get_model("accounts", "DyeingPurchaseOrderItem")
    ReadyPurchaseOrderItem = apps.get_model("accounts", "ReadyPurchaseOrderItem")

    seen = set()

    def add_unit(owner_id, unit_name):
        unit_name = (unit_name or "").strip()
        if not owner_id or not unit_name:
            return
        key = (owner_id, unit_name.lower())
        if key in seen:
            return
        seen.add(key)
        MaterialUnit.objects.get_or_create(owner_id=owner_id, name=unit_name)

    for item in YarnPurchaseOrderItem.objects.select_related("po").iterator():
        add_unit(getattr(item.po, "owner_id", None), item.unit)

    for item in GreigePurchaseOrderItem.objects.select_related("po").iterator():
        add_unit(getattr(item.po, "owner_id", None), item.unit)

    for item in DyeingPurchaseOrderItem.objects.select_related("po").iterator():
        add_unit(getattr(item.po, "owner_id", None), item.unit)

    for item in ReadyPurchaseOrderItem.objects.select_related("po").iterator():
        add_unit(getattr(item.po, "owner_id", None), item.unit)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_brand"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=20)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("owner", "name")},
            },
        ),
        migrations.RunPython(seed_material_units, migrations.RunPython.noop),
    ]