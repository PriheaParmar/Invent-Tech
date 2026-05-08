from django.db import OperationalError, ProgrammingError
from django.urls import reverse

from .models import (
    DyeingPurchaseOrder,
    ERPNotification,
    ERPCompany,
    ERPUserProfile,
    Firm,
    GreigePurchaseOrder,
    ProgramJobberChallan,
    ReadyPurchaseOrder,
    UserExtra,
    YarnPurchaseOrder,
)
from .navigation import get_sidebar_groups, get_utility_groups
from .permissions import actor_allowed_firm_ids, get_actor, get_company, get_permission_codes_for_actor, is_company_admin, is_platform_admin


def _safe_reverse(name, *args, **kwargs):
    try:
        return reverse(f"accounts:{name}", args=args, kwargs=kwargs)
    except Exception:
        return ""


def _sync_notification(owner, object_key, title, message, kind, priority, action_url):
    defaults = {
        "title": title,
        "message": message,
        "kind": kind,
        "priority": priority,
        "action_url": action_url or "",
    }
    notification, created = ERPNotification.objects.get_or_create(
        owner=owner,
        object_key=object_key,
        defaults=defaults,
    )
    if not created:
        changed = False
        for field, value in defaults.items():
            if getattr(notification, field) != value:
                setattr(notification, field, value)
                changed = True
        if changed:
            notification.save(update_fields=[*defaults.keys(), "updated_at"])
    return notification


def _firm_allowed_queryset(request, qs, firm_field="firm_id"):
    firm_ids = actor_allowed_firm_ids(request)
    if firm_ids is None:
        return qs
    return qs.filter(**{f"{firm_field}__in": firm_ids})


def _allowed_notification_keys_for_actor(request):
    """Return object keys visible to the real actor.

    Notifications are stored under the company owner for legacy compatibility.
    For firm-restricted staff, the dropdown must not display company-wide PO,
    challan, inward, or rejection alerts from other firms.
    """
    firm_ids = actor_allowed_firm_ids(request)
    if firm_ids is None:
        return None

    user = request.user
    keys = set()

    for model, label in [
        (YarnPurchaseOrder, "Yarn"),
        (GreigePurchaseOrder, "Greige"),
        (DyeingPurchaseOrder, "Dyeing"),
        (ReadyPurchaseOrder, "Ready"),
    ]:
        label_key = label.lower()
        for pk in model.objects.filter(owner=user, firm_id__in=firm_ids).values_list("pk", flat=True):
            keys.add(f"{label_key}-po-approval-{pk}")
            keys.add(f"{label_key}-po-inward-{pk}")
            keys.add(f"{label_key}-po-rejected-{pk}")

    for pk in ProgramJobberChallan.objects.filter(owner=user, firm_id__in=firm_ids).values_list("pk", flat=True):
        keys.add(f"program-challan-approval-{pk}")
        keys.add(f"program-challan-inward-{pk}")
        keys.add(f"program-challan-rejected-{pk}")

    return keys


def _sync_po_notifications(request, model, label, review_url_name, inward_url_name):
    user = request.user

    pending_pos = _firm_allowed_queryset(request, model.objects.filter(owner=user, approval_status="pending"), "firm_id")
    for po in pending_pos.order_by("-id")[:8]:
        number = getattr(po, "system_number", "") or f"#{po.pk}"
        _sync_notification(
            user,
            f"{label.lower()}-po-approval-{po.pk}",
            f"{label} PO needs approval",
            f"{number} is waiting for approval.",
            "approval",
            "high",
            _safe_reverse(review_url_name, po.pk),
        )

    approved_pos = _firm_allowed_queryset(request, model.objects.filter(owner=user, approval_status="approved"), "firm_id")
    for po in approved_pos.order_by("-id")[:8]:
        try:
            remaining_qty = po.remaining_qty_total
        except Exception:
            remaining_qty = 1
        if remaining_qty and remaining_qty > 0:
            number = getattr(po, "system_number", "") or f"#{po.pk}"
            _sync_notification(
                user,
                f"{label.lower()}-po-inward-{po.pk}",
                f"{label} PO ready for inward",
                f"{number} is approved. You can create inward now.",
                "inward",
                "medium",
                _safe_reverse(inward_url_name, po.pk),
            )

    rejected_pos = _firm_allowed_queryset(request, model.objects.filter(owner=user, approval_status="rejected"), "firm_id")
    for po in rejected_pos.order_by("-updated_at", "-id")[:5]:
        number = getattr(po, "system_number", "") or f"#{po.pk}"
        _sync_notification(
            user,
            f"{label.lower()}-po-rejected-{po.pk}",
            f"{label} PO rejected",
            f"{number} was rejected. Check the reason and update it if needed.",
            "rejected",
            "high",
            _safe_reverse(review_url_name, po.pk),
        )


def _sync_program_challan_notifications(request):
    user = request.user

    pending_qs = (
        _firm_allowed_queryset(request, ProgramJobberChallan.objects.filter(owner=user, status="pending"), "firm_id")
        .select_related("program", "jobber_type", "jobber")
        .order_by("-id")[:10]
    )
    for challan in pending_qs:
        process = getattr(challan.jobber_type, "name", "") or "Jobber"
        program_no = getattr(challan.program, "program_no", "") or f"Program #{challan.program_id}"
        _sync_notification(
            user,
            f"program-challan-approval-{challan.pk}",
            f"{process} challan needs approval",
            f"{challan.challan_no} for {program_no} is waiting for approval.",
            "approval",
            "high",
            _safe_reverse("program_challan_approve", challan.pk),
        )

    approved_qs = (
        _firm_allowed_queryset(request, ProgramJobberChallan.objects.filter(owner=user, status="approved"), "firm_id")
        .select_related("program", "jobber_type")
        .order_by("-updated_at", "-id")[:10]
    )
    for challan in approved_qs:
        if (challan.total_issued_qty or 0) > (challan.inward_qty or 0):
            process = getattr(challan.jobber_type, "name", "") or "Jobber"
            program_no = getattr(challan.program, "program_no", "") or f"Program #{challan.program_id}"
            _sync_notification(
                user,
                f"program-challan-inward-{challan.pk}",
                f"{process} challan ready for inward",
                f"{challan.challan_no} for {program_no} is approved. Inward is pending.",
                "inward",
                "medium",
                _safe_reverse("program_inward_form", challan.pk),
            )

    rejected_qs = (
        _firm_allowed_queryset(request, ProgramJobberChallan.objects.filter(owner=user, status="rejected"), "firm_id")
        .select_related("program", "jobber_type")
        .order_by("-updated_at", "-id")[:5]
    )
    for challan in rejected_qs:
        process = getattr(challan.jobber_type, "name", "") or "Jobber"
        _sync_notification(
            user,
            f"program-challan-rejected-{challan.pk}",
            f"{process} challan rejected",
            f"{challan.challan_no} was rejected. Check and correct it.",
            "rejected",
            "high",
            _safe_reverse("program_challan_approve", challan.pk),
        )


def _notification_context(request):
    if not request.user.is_authenticated:
        return {"erp_notifications": [], "erp_unread_notifications_count": 0}

    actor = get_actor(request)
    if is_platform_admin(actor):
        return {"erp_notifications": [], "erp_unread_notifications_count": 0}

    try:
        _sync_po_notifications(request, YarnPurchaseOrder, "Yarn", "yarnpo_review", "yarnpo_inward")
        _sync_po_notifications(request, GreigePurchaseOrder, "Greige", "greigepo_review", "greigepo_inward")
        _sync_po_notifications(request, DyeingPurchaseOrder, "Dyeing", "dyeingpo_review", "dyeingpo_inward")
        _sync_po_notifications(request, ReadyPurchaseOrder, "Ready", "readypo_review", "readypo_inward")
        _sync_program_challan_notifications(request)

        notification_qs = ERPNotification.objects.filter(owner=request.user)
        allowed_keys = _allowed_notification_keys_for_actor(request)
        if allowed_keys is not None:
            if allowed_keys:
                notification_qs = notification_qs.filter(object_key__in=allowed_keys)
            else:
                notification_qs = notification_qs.none()

        notifications = list(notification_qs.order_by("is_read", "-updated_at", "-id")[:15])
        unread_count = notification_qs.filter(is_read=False).count()
        return {
            "erp_notifications": notifications,
            "erp_unread_notifications_count": unread_count,
        }
    except (OperationalError, ProgrammingError):
        return {"erp_notifications": [], "erp_unread_notifications_count": 0}
    except Exception:
        return {"erp_notifications": [], "erp_unread_notifications_count": 0}


def firm_and_role_context(request):
    if not request.user.is_authenticated:
        return {}

    actor = get_actor(request)
    owner = getattr(request, "erp_owner", None) or request.user
    company = get_company(request)
    current_firm = Firm.objects.filter(owner=owner).order_by("firm_name", "id").first()
    current_user_extra = UserExtra.objects.filter(user=actor).first()

    firm_type_choices = []
    try:
        firm_type_choices = Firm._meta.get_field("firm_type").choices
    except Exception:
        pass

    try:
        erp_permissions = sorted(get_permission_codes_for_actor(actor))
    except Exception:
        erp_permissions = []

    if is_platform_admin(actor):
        admin_scope_label = "Platform Admin"
        admin_scope_note = "Platform controls only"
    elif is_company_admin(request):
        admin_scope_label = "Company Admin"
        admin_scope_note = "Full company access"
    else:
        current_role = getattr(getattr(request, "erp_user_profile", None), "role", None)
        admin_scope_label = getattr(current_role, "name", "Staff") or "Staff"
        allowed_firm_ids = actor_allowed_firm_ids(request)
        if allowed_firm_ids is None:
            admin_scope_note = "Company staff access"
        elif allowed_firm_ids:
            admin_scope_note = f"Restricted to {len(allowed_firm_ids)} firm(s)"
        else:
            admin_scope_note = "No firms assigned"

    context = {
        "current_firm": current_firm,
        "current_user_extra": current_user_extra,
        "current_display_user": actor,
        "current_login_user": actor,
        "current_erp_actor": actor,
        "current_erp_owner": owner,
        "current_data_owner": owner,
        "current_erp_company": company,
        "erp_user_profile": getattr(request, "erp_user_profile", None),
        "erp_permissions": erp_permissions,
        "is_platform_admin": is_platform_admin(actor),
        "is_company_admin": is_company_admin(request),
        "admin_scope_label": admin_scope_label,
        "admin_scope_note": admin_scope_note,
        "FIRM_TYPE_CHOICES": firm_type_choices,
        "ROLE_CHOICES": [],
        "CURRENT_ROLE": getattr(getattr(request, "erp_user_profile", None), "role", None),
        "sidebar_groups": get_sidebar_groups(request),
        "utility_groups": get_utility_groups(request),
    }
    context.update(_notification_context(request))
    return context
