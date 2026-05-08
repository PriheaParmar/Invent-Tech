# Compatibility migration kept only to resolve the earlier/simple role-permission migration name.
# The product-level ERP permission system is defined in 0040_product_tenant_role_permissions.py.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0039_fix_program_inventory_state"),
    ]

    operations = []
