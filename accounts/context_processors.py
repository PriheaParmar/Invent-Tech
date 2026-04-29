from django.db import OperationalError, ProgrammingError
from django.urls import reverse

from .models import (
    DyeingPurchaseOrder,
    ERPNotification,
    Firm,
    GreigePurchaseOrder,
    ProgramJobberChallan,
    ReadyPurchaseOrder,
    UserExtra,
    YarnPurchaseOrder,
)
from .navigation import get_sidebar_groups, get_utility_groups


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


def _sync_po_notifications(request, model, label, review_url_name, inward_url_name):
    user = request.user

    for po in model.objects.filter(owner=user, approval_status="pending").order_by("-id")[:8]:
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

    for po in model.objects.filter(owner=user, approval_status="approved").order_by("-id")[:8]:
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

    for po in model.objects.filter(owner=user, approval_status="rejected").order_by("-updated_at", "-id")[:5]:
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
        ProgramJobberChallan.objects.filter(owner=user, status="pending")
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
        ProgramJobberChallan.objects.filter(owner=user, status="approved")
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
        ProgramJobberChallan.objects.filter(owner=user, status="rejected")
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

    try:
        _sync_po_notifications(request, YarnPurchaseOrder, "Yarn", "yarnpo_review", "yarnpo_inward")
        _sync_po_notifications(request, GreigePurchaseOrder, "Greige", "greigepo_review", "greigepo_inward")
        _sync_po_notifications(request, DyeingPurchaseOrder, "Dyeing", "dyeingpo_review", "dyeingpo_inward")
        _sync_po_notifications(request, ReadyPurchaseOrder, "Ready", "readypo_review", "readypo_inward")
        _sync_program_challan_notifications(request)

        notifications = list(
            ERPNotification.objects.filter(owner=request.user)
            .order_by("is_read", "-updated_at", "-id")[:15]
        )
        unread_count = ERPNotification.objects.filter(owner=request.user, is_read=False).count()
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

    current_firm = Firm.objects.filter(owner=request.user).first()
    current_user_extra = UserExtra.objects.filter(user=request.user).first()

    firm_type_choices = []
    try:
        firm_type_choices = Firm._meta.get_field("firm_type").choices
    except Exception:
        pass

    context = {
        "current_firm": current_firm,
        "current_user_extra": current_user_extra,
        "FIRM_TYPE_CHOICES": firm_type_choices,
        "ROLE_CHOICES": [],
        "CURRENT_ROLE": "",
        "sidebar_groups": get_sidebar_groups(request),
        "utility_groups": get_utility_groups(request),
    }
    context.update(_notification_context(request))
    return context
