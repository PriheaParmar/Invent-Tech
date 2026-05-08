from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Safely resets half-applied ERP permission/audit migration tables so migrations can run cleanly."

    def handle(self, *args, **options):
        tables = [
            "accounts_auditlog",
            "accounts_erpuserprofile_allowed_firms",
            "accounts_erpuserprofile",
            "accounts_erprole",
            "accounts_erpcompany",
        ]
        migrations = [
            "0040_product_tenant_role_permissions",
            "0040_erp_role_permissions",
            "0041_audit_log",
        ]

        with connection.cursor() as cursor:
            self.stdout.write("Dropping half-applied permission/audit tables if they exist...")
            for table in tables:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
                self.stdout.write(f"  OK: {table}")

            placeholders = ",".join(["%s"] * len(migrations))
            cursor.execute(
                f"DELETE FROM django_migrations WHERE app=%s AND name IN ({placeholders})",
                ["accounts", *migrations],
            )
            self.stdout.write("Removed permission/audit migration records if they existed.")

        self.stdout.write(self.style.SUCCESS("Done. Now run: python manage.py migrate"))
