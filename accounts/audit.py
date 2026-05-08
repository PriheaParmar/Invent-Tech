"""Lightweight ERP audit trail helpers and signal registration."""

from __future__ import annotations

from decimal import Decimal
import threading
from typing import Any

from django.apps import apps
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import pre_save, post_save, post_delete
from django.utils import timezone

_audit_state = threading.local()
_audit_signals_registered = False


IGNORED_MODEL_NAMES = {"AuditLog"}
IGNORED_FIELD_NAMES = {"updated_at"}
MAX_TEXT_LENGTH = 260


def set_current_request(request):
    _audit_state.request = request


def clear_current_request():
    if hasattr(_audit_state, "request"):
        delattr(_audit_state, "request")


def get_current_request():
    return getattr(_audit_state, "request", None)


def _safe_str(value: Any, limit: int = MAX_TEXT_LENGTH) -> str:
    try:
        text = str(value)
    except Exception:
        text = repr(value)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _json_value(value: Any):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if hasattr(value, "name") and hasattr(value, "storage"):
        return value.name
    return _safe_str(value)


def _get_ip(request):
    if not request:
        return ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _request_meta(request):
    if not request:
        return {
            "actor": None,
            "owner": None,
            "company": None,
            "actor_username": "system",
            "actor_display": "System",
            "ip": "",
            "user_agent": "",
            "path": "",
            "method": "",
            "session_key": "",
        }

    actor = getattr(request, "erp_actor", None) or getattr(request, "user", None)
    owner = getattr(request, "erp_owner", None) or getattr(request, "user", None)
    company = getattr(request, "erp_company", None)

    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    if owner is not None and not getattr(owner, "is_authenticated", False):
        owner = None

    if company is None and actor is not None:
        try:
            company = actor.erp_profile.company
        except Exception:
            company = None

    username = getattr(actor, "username", "") or "system"
    display = ""
    if actor is not None:
        try:
            display = actor.get_full_name() or actor.username
        except Exception:
            display = username
    display = display or username or "System"

    session_key = ""
    try:
        session_key = request.session.session_key or ""
    except Exception:
        session_key = ""

    return {
        "actor": actor,
        "owner": owner,
        "company": company,
        "actor_username": username,
        "actor_display": display,
        "ip": _get_ip(request),
        "user_agent": (request.META.get("HTTP_USER_AGENT", "") or "")[:500],
        "path": getattr(request, "path", "") or "",
        "method": getattr(request, "method", "") or "",
        "session_key": session_key,
    }


def write_audit_log(
    *,
    action: str,
    message: str = "",
    severity: str = "info",
    module: str = "",
    obj: Any = None,
    object_model: str = "",
    object_pk: str = "",
    object_repr: str = "",
    old_values: dict | None = None,
    new_values: dict | None = None,
    changed_fields: list | None = None,
    extra: dict | None = None,
    status_code: int | None = None,
    request=None,
):
    """Create an audit record without ever breaking the business request."""
    try:
        AuditLog = apps.get_model("accounts", "AuditLog")
    except Exception:
        return None

    try:
        request = request or get_current_request()
        meta = _request_meta(request)

        if obj is not None:
            opts = getattr(obj, "_meta", None)
            if opts:
                object_model = object_model or f"{opts.app_label}.{opts.object_name}"
            object_pk = object_pk or _safe_str(getattr(obj, "pk", "") or "")
            object_repr = object_repr or _safe_str(obj)
            if not module and opts:
                module = opts.app_label

        return AuditLog.objects.create(
            company=meta["company"],
            owner=meta["owner"],
            actor=meta["actor"],
            actor_username=meta["actor_username"],
            actor_display=meta["actor_display"],
            actor_ip=meta["ip"],
            actor_user_agent=meta["user_agent"],
            session_key=meta["session_key"],
            action=action,
            severity=severity,
            module=module[:80],
            object_model=object_model[:150],
            object_pk=object_pk[:80],
            object_repr=object_repr[:260],
            message=message[:500] if message else "",
            path=meta["path"][:300],
            method=meta["method"][:12],
            status_code=status_code,
            old_values=old_values or {},
            new_values=new_values or {},
            changed_fields=changed_fields or [],
            extra=extra or {},
        )
    except Exception:
        return None


def _snapshot_instance(instance):
    data = {}
    opts = getattr(instance, "_meta", None)
    if not opts:
        return data
    for field in opts.concrete_fields:
        if field.name in IGNORED_FIELD_NAMES:
            continue
        try:
            value = field.value_from_object(instance)
        except Exception:
            continue
        data[field.name] = _json_value(value)
    return data


def _is_ignored_model(sender):
    opts = getattr(sender, "_meta", None)
    if not opts:
        return True
    if opts.app_label != "accounts":
        return True
    if opts.object_name in IGNORED_MODEL_NAMES:
        return True
    return False


def _audit_pre_save(sender, instance, **kwargs):
    if _is_ignored_model(sender):
        return
    if getattr(instance, "_skip_audit", False):
        return
    if not getattr(instance, "pk", None):
        instance._audit_old_values = {}
        return
    try:
        old = sender._default_manager.get(pk=instance.pk)
        instance._audit_old_values = _snapshot_instance(old)
    except Exception:
        instance._audit_old_values = {}


def _audit_post_save(sender, instance, created, **kwargs):
    if _is_ignored_model(sender):
        return
    if getattr(instance, "_skip_audit", False):
        return

    try:
        opts = instance._meta
        new_values = _snapshot_instance(instance)
        object_model = f"{opts.app_label}.{opts.object_name}"
        module = opts.verbose_name_plural.title()

        if created:
            write_audit_log(
                action="create",
                severity="info",
                module=module,
                obj=instance,
                object_model=object_model,
                message=f"Created {opts.verbose_name}: {_safe_str(instance)}",
                new_values=new_values,
                changed_fields=list(new_values.keys())[:80],
            )
            return

        old_values = getattr(instance, "_audit_old_values", {}) or {}
        changed_fields = []
        old_changed = {}
        new_changed = {}
        for key, new_value in new_values.items():
            if key in IGNORED_FIELD_NAMES:
                continue
            old_value = old_values.get(key)
            if old_value != new_value:
                changed_fields.append(key)
                old_changed[key] = old_value
                new_changed[key] = new_value

        if not changed_fields:
            return

        action = "update"
        severity = "info"
        message = f"Updated {opts.verbose_name}: {_safe_str(instance)}"
        status_value = new_changed.get("approval_status", new_changed.get("status"))
        if isinstance(status_value, str):
            status_lower = status_value.lower()
            if status_lower == "approved":
                action = "approve"
                message = f"Approved {opts.verbose_name}: {_safe_str(instance)}"
            elif status_lower == "rejected":
                action = "reject"
                severity = "warning"
                message = f"Rejected {opts.verbose_name}: {_safe_str(instance)}"

        write_audit_log(
            action=action,
            severity=severity,
            module=module,
            obj=instance,
            object_model=object_model,
            message=message,
            old_values=old_changed,
            new_values=new_changed,
            changed_fields=changed_fields,
        )
    except Exception:
        return


def _audit_post_delete(sender, instance, **kwargs):
    if _is_ignored_model(sender):
        return
    if getattr(instance, "_skip_audit", False):
        return
    try:
        opts = instance._meta
        write_audit_log(
            action="delete",
            severity="warning",
            module=opts.verbose_name_plural.title(),
            obj=instance,
            object_model=f"{opts.app_label}.{opts.object_name}",
            message=f"Deleted {opts.verbose_name}: {_safe_str(instance)}",
            old_values=_snapshot_instance(instance),
            changed_fields=list(_snapshot_instance(instance).keys())[:80],
        )
    except Exception:
        return


def _login_success(sender, request, user, **kwargs):
    write_audit_log(
        action="login",
        severity="info",
        module="Authentication",
        message=f"{getattr(user, 'username', 'User')} logged in",
        request=request,
        extra={"username": getattr(user, "username", "")},
    )


def _logout_success(sender, request, user, **kwargs):
    write_audit_log(
        action="logout",
        severity="info",
        module="Authentication",
        message=f"{getattr(user, 'username', 'User')} logged out",
        request=request,
        extra={"username": getattr(user, "username", "") if user else ""},
    )


def _login_failed(sender, credentials, request, **kwargs):
    username = ""
    try:
        username = credentials.get("username", "") or credentials.get("email", "") or ""
    except Exception:
        username = ""
    write_audit_log(
        action="login_failed",
        severity="warning",
        module="Authentication",
        message=f"Failed login attempt for {username or 'unknown user'}",
        request=request,
        extra={"username": username},
    )


def register_audit_signals():
    global _audit_signals_registered
    if _audit_signals_registered:
        return
    _audit_signals_registered = True

    for model in apps.get_models(include_auto_created=False):
        if _is_ignored_model(model):
            continue
        uid_base = f"erp_audit_{model._meta.label_lower}"
        pre_save.connect(_audit_pre_save, sender=model, dispatch_uid=f"{uid_base}_pre")
        post_save.connect(_audit_post_save, sender=model, dispatch_uid=f"{uid_base}_post")
        post_delete.connect(_audit_post_delete, sender=model, dispatch_uid=f"{uid_base}_delete")

    user_logged_in.connect(_login_success, dispatch_uid="erp_audit_login_success")
    user_logged_out.connect(_logout_success, dispatch_uid="erp_audit_logout_success")
    user_login_failed.connect(_login_failed, dispatch_uid="erp_audit_login_failed")
