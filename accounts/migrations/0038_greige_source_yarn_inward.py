from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0037_remove_client_client_code_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="greigepurchaseorder",
            name="source_yarn_inward",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="generated_greige_pos",
                to="accounts.yarnpoinward",
            ),
        ),
    ]