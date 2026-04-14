from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0036_termscondition"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="client",
            name="client_code",
        ),
        migrations.RemoveField(
            model_name="client",
            name="shipping_address",
        ),
        migrations.AlterField(
            model_name="client",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]