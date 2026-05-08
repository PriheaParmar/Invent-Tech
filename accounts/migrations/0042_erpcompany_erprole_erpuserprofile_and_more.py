# Compatibility migration.
# A broken generated 0042 migration previously tried to create ERPCompany again
# and remove old ERPAccountRole/ERPUserAccess models that are not present in the
# current migration state. That caused migration-state crashes.
#
# The actual ERPCompany/ERPRole/ERPUserProfile state is now restored in:
#   0041_erpcompany_erprole_erpuserprofile_and_more.py
# and AuditLog depends on it before referencing accounts.ERPCompany.

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0041_audit_log"),
    ]

    operations = []
