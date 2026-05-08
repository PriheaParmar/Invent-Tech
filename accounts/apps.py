from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        try:
            from .audit import register_audit_signals
            register_audit_signals()
        except Exception:
            # Audit trail should never block app startup.
            pass
