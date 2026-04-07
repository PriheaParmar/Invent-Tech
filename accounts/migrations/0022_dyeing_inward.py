from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_greigepoinward_dyeingpurchaseorder_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DyeingPOInward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("inward_number", models.CharField(max_length=30, unique=True)),
                ("inward_date", models.DateField(default=django.utils.timezone.localdate)),
                ("notes", models.TextField(blank=True, default="")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accounts_dyeingpoinward_set", to="auth.user")),
                ("po", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inwards", to="accounts.dyeingpurchaseorder")),
            ],
            options={"ordering": ["-inward_date", "-id"]},
        ),
        migrations.CreateModel(
            name="DyeingPOInwardItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("remark", models.CharField(blank=True, default="", max_length=255)),
                ("inward", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="accounts.dyeingpoinward")),
                ("po_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inward_items", to="accounts.dyeingpurchaseorderitem")),
            ],
            options={"unique_together": {("inward", "po_item")}},
        ),
    ]
    