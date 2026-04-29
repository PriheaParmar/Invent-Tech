# Generated merge migration to resolve conflicting 0037 leaf migrations.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0037_rename_accounts_er_owner_i_3e6458_idx_accounts_er_owner_i_d861b6_idx_and_more'),
        ('accounts', '0037_po_inward_qc_fields'),
    ]

    operations = []
