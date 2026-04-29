# Generated manually for PO inward dyeing-style fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0036_erpnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="received_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="accepted_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="rejected_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="hold_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="actual_rolls",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="actual_gsm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="actual_width",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="dye_lot_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="batch_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="shade_reference",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="yarnpoinwarditem",
            name="qc_status",
            field=models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("partial", "Partial"), ("hold", "Hold"), ("rejected", "Rejected")], default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="received_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="accepted_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="rejected_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="hold_qty",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="actual_rolls",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="actual_gsm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="actual_width",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="dye_lot_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="batch_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="shade_reference",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="greigepoinwarditem",
            name="qc_status",
            field=models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("partial", "Partial"), ("hold", "Hold"), ("rejected", "Rejected")], default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="readypoinward",
            name="vendor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ready_inwards", to="accounts.vendor"),
        ),
        migrations.AddField(
            model_name="readypoinward",
            name="inward_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ready_inwards", to="accounts.inwardtype"),
        ),
        migrations.AddField(
            model_name="readypoinwarditem",
            name="dye_lot_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="readypoinwarditem",
            name="batch_no",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="readypoinwarditem",
            name="shade_reference",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
