# Safe product-level tenant + role permission migration.
# This file is intentionally kept with the original 0041 name because some
# existing development databases already have this migration recorded as applied.
# It provides the migration STATE for ERPCompany/ERPRole/ERPUserProfile before
# AuditLog references ERPCompany.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


CREATE_PERMISSION_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS accounts_erpcompany (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    name varchar(180) NOT NULL,
    slug varchar(180) NOT NULL,
    contact_person varchar(120) NOT NULL DEFAULT '',
    phone varchar(20) NOT NULL DEFAULT '',
    email varchar(254) NOT NULL DEFAULT '',
    status varchar(20) NOT NULL DEFAULT 'active',
    subscription_start date NULL,
    subscription_end date NULL,
    notes text NOT NULL DEFAULT '',
    created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    admin_user_id integer NOT NULL UNIQUE REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE UNIQUE INDEX IF NOT EXISTS accounts_erpcompany_slug_uniq
    ON accounts_erpcompany(slug);
CREATE INDEX IF NOT EXISTS accounts_erpcompany_admin_user_id_idx
    ON accounts_erpcompany(admin_user_id);

CREATE TABLE IF NOT EXISTS accounts_erprole (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    name varchar(120) NOT NULL,
    description text NOT NULL DEFAULT '',
    permissions text NOT NULL DEFAULT '[]',
    is_active bool NOT NULL DEFAULT 1,
    created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    company_id bigint NOT NULL REFERENCES accounts_erpcompany(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE UNIQUE INDEX IF NOT EXISTS accounts_erprole_company_name_uniq
    ON accounts_erprole(company_id, name);
CREATE INDEX IF NOT EXISTS accounts_erprole_company_id_idx
    ON accounts_erprole(company_id);

CREATE TABLE IF NOT EXISTS accounts_erpuserprofile (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_type varchar(30) NOT NULL DEFAULT 'staff',
    phone varchar(20) NOT NULL DEFAULT '',
    designation varchar(80) NOT NULL DEFAULT '',
    department varchar(80) NOT NULL DEFAULT '',
    is_active bool NOT NULL DEFAULT 1,
    created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    company_id bigint NOT NULL REFERENCES accounts_erpcompany(id) DEFERRABLE INITIALLY DEFERRED,
    role_id bigint NULL REFERENCES accounts_erprole(id) DEFERRABLE INITIALLY DEFERRED,
    user_id integer NOT NULL UNIQUE REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS accounts_erpuserprofile_company_id_idx
    ON accounts_erpuserprofile(company_id);
CREATE INDEX IF NOT EXISTS accounts_erpuserprofile_role_id_idx
    ON accounts_erpuserprofile(role_id);
CREATE INDEX IF NOT EXISTS accounts_erpuserprofile_user_id_idx
    ON accounts_erpuserprofile(user_id);

CREATE TABLE IF NOT EXISTS accounts_erpuserprofile_allowed_firms (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    erpuserprofile_id bigint NOT NULL REFERENCES accounts_erpuserprofile(id) DEFERRABLE INITIALLY DEFERRED,
    firm_id bigint NOT NULL REFERENCES accounts_firm(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE UNIQUE INDEX IF NOT EXISTS accounts_erpuserprofile_allowed_firms_uniq
    ON accounts_erpuserprofile_allowed_firms(erpuserprofile_id, firm_id);
CREATE INDEX IF NOT EXISTS accounts_erpuserprofile_allowed_firms_profile_idx
    ON accounts_erpuserprofile_allowed_firms(erpuserprofile_id);
CREATE INDEX IF NOT EXISTS accounts_erpuserprofile_allowed_firms_firm_idx
    ON accounts_erpuserprofile_allowed_firms(firm_id);
"""


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0040_erp_role_permissions"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(CREATE_PERMISSION_TABLES_SQL, reverse_sql=migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="ERPCompany",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=180)),
                        ("slug", models.SlugField(max_length=180, unique=True)),
                        ("contact_person", models.CharField(blank=True, default="", max_length=120)),
                        ("phone", models.CharField(blank=True, default="", max_length=20)),
                        ("email", models.EmailField(blank=True, default="", max_length=254)),
                        ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("trial", "Trial"), ("suspended", "Suspended")], default="active", max_length=20)),
                        ("subscription_start", models.DateField(blank=True, null=True)),
                        ("subscription_end", models.DateField(blank=True, null=True)),
                        ("notes", models.TextField(blank=True, default="")),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("admin_user", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="erp_company_admin", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "verbose_name": "ERP Company",
                        "verbose_name_plural": "ERP Companies",
                        "ordering": ["name"],
                    },
                ),
                migrations.CreateModel(
                    name="ERPRole",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=120)),
                        ("description", models.TextField(blank=True, default="")),
                        ("permissions", models.JSONField(blank=True, default=list)),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="roles", to="accounts.erpcompany")),
                    ],
                    options={
                        "ordering": ["name"],
                        "unique_together": {("company", "name")},
                    },
                ),
                migrations.CreateModel(
                    name="ERPUserProfile",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("user_type", models.CharField(choices=[("company_admin", "Company Admin"), ("staff", "Staff User")], default="staff", max_length=30)),
                        ("phone", models.CharField(blank=True, default="", max_length=20)),
                        ("designation", models.CharField(blank=True, default="", max_length=80)),
                        ("department", models.CharField(blank=True, default="", max_length=80)),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("allowed_firms", models.ManyToManyField(blank=True, related_name="allowed_user_profiles", to="accounts.firm")),
                        ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_profiles", to="accounts.erpcompany")),
                        ("role", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_profiles", to="accounts.erprole")),
                        ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="erp_profile", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "ordering": ["company__name", "user__username"],
                    },
                ),
            ],
        ),
        migrations.AlterField(
            model_name="firm",
            name="owner",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="firms", to=settings.AUTH_USER_MODEL),
        ),
    ]
