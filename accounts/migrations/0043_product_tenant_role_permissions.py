# Safe product-level tenant + role permission migration.
# This migration is idempotent for SQLite dev databases:
# if a previous failed run already created one of these tables, it will continue safely.

from django.conf import settings
from django.db import migrations


def _unique_slug(Company, base_slug):
    slug = base_slug or "company"
    candidate = slug
    counter = 1
    while Company.objects.filter(slug=candidate).exists():
        counter += 1
        candidate = f"{slug}-{counter}"
    return candidate


def _historical_user_full_name(user):
    # Historical models returned by apps.get_model() inside migrations do not
    # include custom/model methods like User.get_full_name(). Build it from
    # fields safely instead.
    first_name = (getattr(user, "first_name", "") or "").strip()
    last_name = (getattr(user, "last_name", "") or "").strip()
    return " ".join(part for part in [first_name, last_name] if part).strip()


def create_legacy_companies(apps, schema_editor):
    from django.utils.text import slugify

    User = apps.get_model("auth", "User")
    Firm = apps.get_model("accounts", "Firm")
    ERPCompany = apps.get_model("accounts", "ERPCompany")
    ERPUserProfile = apps.get_model("accounts", "ERPUserProfile")

    owner_ids = set(Firm.objects.exclude(owner_id=None).values_list("owner_id", flat=True))
    if not owner_ids:
        owner_ids = set(User.objects.filter(is_superuser=True).values_list("id", flat=True))

    for user in User.objects.filter(id__in=owner_ids):
        if ERPCompany.objects.filter(admin_user_id=user.id).exists():
            continue

        full_name = _historical_user_full_name(user)
        username = (getattr(user, "username", "") or "").strip()
        email = (getattr(user, "email", "") or "").strip()

        first_firm = Firm.objects.filter(owner_id=user.id).order_by("firm_name", "id").first()
        company_name = first_firm.firm_name if first_firm else (full_name or username or f"Company {user.id}")
        base_slug = slugify(company_name) or f"company-{user.id}"
        company = ERPCompany.objects.create(
            name=company_name,
            slug=_unique_slug(ERPCompany, base_slug),
            admin_user_id=user.id,
            contact_person=full_name or username,
            email=email,
            status="active",
        )
        ERPUserProfile.objects.update_or_create(
            user_id=user.id,
            defaults={
                "company_id": company.id,
                "user_type": "company_admin",
                "is_active": True,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


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
        ("accounts", "0042_erpcompany_erprole_erpuserprofile_and_more"),
    ]

    operations = [
        migrations.RunSQL(CREATE_PERMISSION_TABLES_SQL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(create_legacy_companies, noop_reverse),
    ]
