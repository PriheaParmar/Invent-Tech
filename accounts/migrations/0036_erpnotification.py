# Generated manually for InventTech ERP notifications

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0035_greigepurchaseorder_remarks_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ERPNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("object_key", models.CharField(max_length=120)),
                ("title", models.CharField(max_length=160)),
                ("message", models.TextField(blank=True, default="")),
                ("kind", models.CharField(choices=[("approval", "Approval Needed"), ("inward", "Ready For Inward"), ("rejected", "Rejected"), ("pending", "Pending"), ("info", "Information")], default="info", max_length=30)),
                ("priority", models.CharField(choices=[("high", "High"), ("medium", "Medium"), ("low", "Low")], default="low", max_length=20)),
                ("action_url", models.CharField(blank=True, default="", max_length=300)),
                ("is_read", models.BooleanField(default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["is_read", "-updated_at", "-id"],
                "unique_together": {("owner", "object_key")},
                "indexes": [
                    models.Index(fields=["owner", "is_read"], name="accounts_er_owner_i_3e6458_idx"),
                    models.Index(fields=["owner", "kind"], name="accounts_er_owner_k_0d4c1d_idx"),
                ],
            },
        ),
    ]
