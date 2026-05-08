from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


CREATE_AUDIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS accounts_auditlog (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    actor_username varchar(150) NOT NULL DEFAULT '',
    actor_display varchar(180) NOT NULL DEFAULT '',
    actor_ip varchar(80) NOT NULL DEFAULT '',
    actor_user_agent text NOT NULL DEFAULT '',
    session_key varchar(80) NOT NULL DEFAULT '',
    action varchar(40) NOT NULL DEFAULT 'other',
    severity varchar(20) NOT NULL DEFAULT 'info',
    module varchar(80) NOT NULL DEFAULT '',
    object_model varchar(150) NOT NULL DEFAULT '',
    object_pk varchar(80) NOT NULL DEFAULT '',
    object_repr varchar(260) NOT NULL DEFAULT '',
    message varchar(500) NOT NULL DEFAULT '',
    path varchar(300) NOT NULL DEFAULT '',
    method varchar(12) NOT NULL DEFAULT '',
    status_code integer unsigned NULL CHECK (status_code >= 0),
    old_values text NOT NULL DEFAULT '{}',
    new_values text NOT NULL DEFAULT '{}',
    changed_fields text NOT NULL DEFAULT '[]',
    extra text NOT NULL DEFAULT '{}',
    created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id integer NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED,
    company_id bigint NULL REFERENCES accounts_erpcompany(id) DEFERRABLE INITIALLY DEFERRED,
    owner_id integer NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS accounts_au_company_a2c894_idx
    ON accounts_auditlog(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS accounts_au_owner_3c65ae_idx
    ON accounts_auditlog(owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS accounts_au_actor_824dda_idx
    ON accounts_auditlog(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS accounts_au_action_d914c9_idx
    ON accounts_auditlog(action, created_at DESC);
CREATE INDEX IF NOT EXISTS accounts_au_severit_5ab333_idx
    ON accounts_auditlog(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS accounts_au_object__663ce6_idx
    ON accounts_auditlog(object_model, object_pk);
"""


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0041_erpcompany_erprole_erpuserprofile_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(CREATE_AUDIT_TABLE_SQL, reverse_sql=migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="AuditLog",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("actor_username", models.CharField(blank=True, default="", max_length=150)),
                        ("actor_display", models.CharField(blank=True, default="", max_length=180)),
                        ("actor_ip", models.CharField(blank=True, default="", max_length=80)),
                        ("actor_user_agent", models.TextField(blank=True, default="")),
                        ("session_key", models.CharField(blank=True, default="", max_length=80)),
                        ("action", models.CharField(choices=[("create", "Created"), ("update", "Updated"), ("delete", "Deleted"), ("login", "Login"), ("logout", "Logout"), ("login_failed", "Login Failed"), ("http_error", "HTTP Error"), ("exception", "Exception"), ("export", "Export"), ("approve", "Approved"), ("reject", "Rejected"), ("other", "Other")], default="other", max_length=40)),
                        ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("security", "Security")], default="info", max_length=20)),
                        ("module", models.CharField(blank=True, default="", max_length=80)),
                        ("object_model", models.CharField(blank=True, default="", max_length=150)),
                        ("object_pk", models.CharField(blank=True, default="", max_length=80)),
                        ("object_repr", models.CharField(blank=True, default="", max_length=260)),
                        ("message", models.CharField(blank=True, default="", max_length=500)),
                        ("path", models.CharField(blank=True, default="", max_length=300)),
                        ("method", models.CharField(blank=True, default="", max_length=12)),
                        ("status_code", models.PositiveIntegerField(blank=True, null=True)),
                        ("old_values", models.JSONField(blank=True, default=dict)),
                        ("new_values", models.JSONField(blank=True, default=dict)),
                        ("changed_fields", models.JSONField(blank=True, default=list)),
                        ("extra", models.JSONField(blank=True, default=dict)),
                        ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                        ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="actor_audit_logs", to=settings.AUTH_USER_MODEL)),
                        ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="accounts.erpcompany")),
                        ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_audit_logs", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "verbose_name": "Audit Log",
                        "verbose_name_plural": "Audit Logs",
                        "ordering": ["-created_at", "-id"],
                    },
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["company", "-created_at"], name="accounts_au_company_a2c894_idx"),
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["owner", "-created_at"], name="accounts_au_owner_3c65ae_idx"),
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["actor", "-created_at"], name="accounts_au_actor_824dda_idx"),
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["action", "-created_at"], name="accounts_au_action_d914c9_idx"),
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["severity", "-created_at"], name="accounts_au_severit_5ab333_idx"),
                ),
                migrations.AddIndex(
                    model_name="auditlog",
                    index=models.Index(fields=["object_model", "object_pk"], name="accounts_au_object__663ce6_idx"),
                ),
            ],
        )
    ]
