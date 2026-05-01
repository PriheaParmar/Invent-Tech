# Generated manually for QA fix batch: program status + owner-safe inventory lots.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_merge_0037_notifications_po_inward"),
    ]

    operations = [
        migrations.AlterField(
            model_name="program",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_progress", "In Progress"),
                    ("closed", "Closed"),
                ],
                default="open",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="inventorylot",
            name="lot_code",
            field=models.CharField(max_length=80),
        ),
        migrations.AddConstraint(
            model_name="inventorylot",
            constraint=models.UniqueConstraint(
                fields=("owner", "lot_code"),
                name="unique_inventory_lot_per_owner",
            ),
        ),
    ]
