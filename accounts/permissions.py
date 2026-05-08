from collections import OrderedDict

from django.urls import reverse

# Central permission registry.
# Code format: module.action. Keep these stable because roles store them in DB.
PERMISSION_GROUPS = OrderedDict([
    ("Dashboard", [
        ("dashboard.view", "View dashboard"),
    ]),
    ("System Health", [
        ("system_health.view", "View system health and error log"),
        ("activity_log.view", "View admin audit trail and activity log"),
    ]),
    ("Company Setup", [
        ("platform.manage", "Platform: manage ERP companies"),
        ("settings.manage", "Company: manage roles and users"),
        ("firm.view", "View firms"),
        ("firm.manage", "Add/edit/delete firms"),
    ]),
    ("Masters / Utilities", [
        ("master.view", "View masters/utilities"),
        ("master.add", "Add masters"),
        ("master.edit", "Edit masters"),
        ("master.delete", "Delete masters"),
    ]),
    ("Yarn Purchase", [
        ("yarn_po.view", "View Yarn PO"),
        ("yarn_po.add", "Add Yarn PO"),
        ("yarn_po.edit", "Edit Yarn PO"),
        ("yarn_po.delete", "Delete Yarn PO"),
        ("yarn_po.review", "Approve/reject Yarn PO"),
        ("yarn_po.inward", "Yarn PO inward"),
        ("yarn_po.pdf", "Download Yarn PO PDF"),
    ]),
    ("Greige Purchase", [
        ("greige_po.view", "View Greige PO"),
        ("greige_po.add", "Add Greige PO"),
        ("greige_po.edit", "Edit Greige PO"),
        ("greige_po.delete", "Delete Greige PO"),
        ("greige_po.review", "Approve/reject Greige PO"),
        ("greige_po.inward", "Greige PO inward"),
        ("greige_po.pdf", "Download Greige PO PDF"),
    ]),
    ("Dyeing Purchase", [
        ("dyeing_po.view", "View Dyeing PO"),
        ("dyeing_po.add", "Add Dyeing PO"),
        ("dyeing_po.edit", "Edit Dyeing PO"),
        ("dyeing_po.delete", "Delete Dyeing PO"),
        ("dyeing_po.review", "Approve/reject Dyeing PO"),
        ("dyeing_po.inward", "Dyeing PO inward"),
        ("dyeing_po.pdf", "Download Dyeing PO PDF"),
    ]),
    ("Ready Purchase", [
        ("ready_po.view", "View Ready PO"),
        ("ready_po.add", "Add Ready PO"),
        ("ready_po.edit", "Edit Ready PO"),
        ("ready_po.delete", "Delete Ready PO"),
        ("ready_po.review", "Approve/reject Ready PO"),
        ("ready_po.inward", "Ready PO inward"),
        ("ready_po.pdf", "Download Ready PO PDF"),
    ]),
    ("Production / Programs", [
        ("program.view", "View programs"),
        ("program.add", "Add programs"),
        ("program.edit", "Edit programs"),
        ("program.delete", "Delete programs"),
        ("program.verify", "Verify programs"),
        ("program.start", "Start programs"),
        ("program.challan", "Generate/manage challans"),
        ("program.approve_challan", "Approve/reject challans"),
        ("program.inward", "Program inward"),
        ("program.costing", "Program costing"),
    ]),
    ("Inventory / QC / QR", [
        ("inventory.view", "View inventory"),
        ("inventory.manage", "Manage inventory lots"),
        ("qc.view", "View QC"),
        ("qc.manage", "Create/edit QC"),
        ("qr.view", "View QR labels"),
        ("qr.manage", "Create/scan QR labels"),
        ("costing.view", "View costing"),
        ("costing.manage", "Create costing snapshots"),
    ]),
    ("Sales", [
        ("dispatch.view", "View dispatch"),
        ("dispatch.manage", "Create/edit dispatch"),
        ("invoice.view", "View invoices"),
        ("invoice.manage", "Create/edit invoices"),
    ]),
    ("Reports", [
        ("reports.view", "View reports"),
        ("reports.export", "Export reports"),
    ]),
    ("Maintenance", [
        ("maintenance.view", "View maintenance"),
        ("maintenance.manage", "Manage maintenance"),
    ]),
])

ALL_PERMISSION_CODES = [code for group in PERMISSION_GROUPS.values() for code, _ in group]

# Platform super admin must stay a product/system admin, not a silent company admin.
PLATFORM_ADMIN_PERMISSION_CODES = {
    "dashboard.view",
    "platform.manage",
    "system_health.view",
    "activity_log.view",
    # Allow platform/admin login to open and submit the Dyeing PO review popup.
    # Company activity logs remain protected by activity_log.view above.
    "dyeing_po.view",
    "dyeing_po.review",
}

# Company admins control their own company ERP, but not platform/company subscription controls.
COMPANY_ADMIN_BLOCKED_PERMISSION_CODES = {
    "platform.manage",
    "system_health.view",
}
COMPANY_ADMIN_PERMISSION_CODES = set(ALL_PERMISSION_CODES) - COMPANY_ADMIN_BLOCKED_PERMISSION_CODES

# Staff roles must never receive admin/system owner permissions even if old role JSON contains them.
STAFF_BLOCKED_PERMISSION_CODES = {
    "platform.manage",
    "settings.manage",
    "system_health.view",
    "activity_log.view",
}

# These permissions should not be assignable inside company staff role forms.
ROLE_FORBIDDEN_PERMISSION_CODES = STAFF_BLOCKED_PERMISSION_CODES


SIDEBAR_PERMISSION_BY_URL_NAME = {
    "accounts:dashboard": "dashboard.view",
    "accounts:utilities": "master.view",
    "accounts:po_home": "yarn_po.view",
    "accounts:program_list": "program.view",
    "accounts:reports_home": "reports.view",
    "accounts:stock_lot_wise": "inventory.view",
    "accounts:dispatch_list": "dispatch.view",
    "accounts:invoice_list": "invoice.view",
    "accounts:quality_check_list": "qc.view",
    "accounts:inventory_lot_list": "inventory.view",
    "accounts:qr_code_add": "qr.manage",
    "accounts:costing_snapshot_list": "costing.view",
    "accounts:maintenance_list": "maintenance.view",
    "accounts:role_list": "settings.manage",
    "accounts:platform_company_list": "platform.manage",
    "accounts:system_health": "system_health.view",
    "accounts:activity_log": "activity_log.view",
}


def _has_any(user_permissions, *codes):
    return any(code in user_permissions for code in codes)


URL_PERMISSION_RULES = {
    # Company/platform setup
    "platform_company_list": "platform.manage",
    "platform_company_create": "platform.manage",
    "platform_company_update": "platform.manage",
    "platform_company_toggle": "platform.manage",
    "role_list": "settings.manage",
    "role_create": "settings.manage",
    "role_update": "settings.manage",
    "role_delete": "settings.manage",
    "team_user_create": "settings.manage",
    "team_user_update": "settings.manage",
    "team_user_toggle": "settings.manage",
    "system_health": "system_health.view",
    "activity_log": "activity_log.view",

    # Firm
    "firm": "firm.view",
    "firm_list": "firm.view",
    "firm_add": "firm.manage",
    "firm_edit": "firm.manage",
    "firm_delete": "firm.manage",
    "firm_save": "firm.manage",

    # Purchase home
    "po_home": "yarn_po.view",

    # Yarn PO
    "yarnpo_list": "yarn_po.view",
    "yarnpo_add": "yarn_po.add",
    "yarnpo_edit": "yarn_po.edit",
    "yarnpo_delete": "yarn_po.delete",
    "yarnpo_review": "yarn_po.review",
    "yarnpo_inward": "yarn_po.inward",
    "yarn_inward_edit": "yarn_po.inward",
    "yarn_inward_tracker": "yarn_po.inward",
    "yarnpo_pdf": "yarn_po.pdf",
    "generate_greige_po_from_yarn": "greige_po.add",

    # Greige PO
    "greigepo_list": "greige_po.view",
    "greigepo_add": "greige_po.add",
    "greigepo_create": "greige_po.add",
    "greigepo_edit": "greige_po.edit",
    "greigepo_update": "greige_po.edit",
    "greigepo_delete": "greige_po.delete",
    "greigepo_review": "greige_po.review",
    "greigepo_inward": "greige_po.inward",
    "greige_inward_edit": "greige_po.inward",
    "greige_inward_tracker": "greige_po.inward",
    "greigepo_pdf": "greige_po.pdf",
    "generate_dyeing_po_from_greige": "dyeing_po.add",

    # Dyeing PO
    "dyeingpo_list": "dyeing_po.view",
    "dyeingpo_add": "dyeing_po.add",
    "dyeingpo_create": "dyeing_po.add",
    "dyeingpo_edit": "dyeing_po.edit",
    "dyeingpo_update": "dyeing_po.edit",
    "dyeingpo_delete": "dyeing_po.delete",
    "dyeingpo_review": "dyeing_po.review",
    "dyeingpo_inward": "dyeing_po.inward",
    "dyeing_inward_edit": "dyeing_po.inward",
    "dyeing_inward_delete": "dyeing_po.inward",
    "dyeing_inward_tracker": "dyeing_po.inward",
    "dyeingpo_pdf": "dyeing_po.pdf",
    "generate_ready_po_from_dyeing": "ready_po.add",

    # Ready PO
    "readypo_list": "ready_po.view",
    "readypo_add": "ready_po.add",
    "readypo_create": "ready_po.add",
    "readypo_edit": "ready_po.edit",
    "readypo_update": "ready_po.edit",
    "readypo_delete": "ready_po.delete",
    "readypo_review": "ready_po.review",
    "readypo_inward": "ready_po.inward",
    "ready_inward_edit": "ready_po.inward",
    "ready_inward_tracker": "ready_po.inward",
    "readypo_pdf": "ready_po.pdf",

    # Programs
    "program_list": "program.view",
    "program_create": "program.add",
    "program_update": "program.edit",
    "program_delete": "program.delete",
    "program_verify": "program.verify",
    "program_start": "program.start",
    "program_challan_manage": "program.challan",
    "program_challan_create": "program.challan",
    "program_challan_detail": "program.challan",
    "program_challan_print": "program.challan",
    "program_challan_approve": "program.approve_challan",
    "program_inward_form": "program.inward",
    "program_costing_detail": "program.costing",

    # Inventory / QC / QR / Costing
    "inventory_lot_list": "inventory.view",
    "inventory_lot_create": "inventory.manage",
    "inventory_lot_update": "inventory.manage",
    "inventory_lot_delete": "inventory.manage",
    "stock_lot_wise": "inventory.view",
    "quality_check_list": "qc.view",
    "quality_check_create": "qc.manage",
    "quality_check_update": "qc.manage",
    "quality_check_delete": "qc.manage",
    "qr_code_list": "qr.view",
    "qr_code_add": "qr.manage",
    "qr_code_update": "qr.manage",
    "qr_code_scan": "qr.manage",
    "costing_snapshot_list": "costing.view",
    "costing_snapshot_create": "costing.manage",
    "costing_snapshot_update": "costing.manage",

    # Reports
    "reports_home": "reports.view",
    "report_jobber_type_wise": "reports.view",
    "report_program_production": "reports.view",
    "report_ready_po_details": "reports.view",
    "report_stitching_inwards": "reports.view",
    "report_used_lot_summary": "reports.view",
    "report_greige_po_status": "reports.view",
    "report_yarn_po_status": "reports.view",
    "report_dyeing_po_status": "reports.view",
    "report_inventory_lot_stock": "reports.view",
    "report_program_stage_flow": "reports.view",
    "report_dispatch_pending": "reports.view",
    "report_jobber_type_wise_excel": "reports.export",
    "report_program_production_excel": "reports.export",

    # Sales / maintenance
    "dispatch_list": "dispatch.view",
    "dispatch_create": "dispatch.manage",
    "dispatch_update": "dispatch.manage",
    "dispatch_delete": "dispatch.manage",
    "invoice_list": "invoice.view",
    "invoice_create": "invoice.manage",
    "invoice_update": "invoice.manage",
    "invoice_delete": "invoice.manage",
    "maintenance_list": "maintenance.view",
    "maintenance_create": "maintenance.manage",
    "maintenance_update": "maintenance.manage",
    "maintenance_delete": "maintenance.manage",
}


MASTER_URL_PREFIXES = (
    "jobber", "jobbertype", "material", "materialtype", "materialsubtype",
    "materialshade", "materialunit", "accessory", "party", "client", "vendor",
    "location", "brand", "category", "maincategory", "subcategory", "expense",
    "patterntype", "catalogue", "dyeing_material_link", "dyeing_other_charge",
    "termscondition", "inwardtype", "bom",
)


def permission_for_url_name(url_name):
    if not url_name:
        return ""

    direct = URL_PERMISSION_RULES.get(url_name)
    if direct:
        return direct

    if url_name.startswith("report_"):
        return "reports.export" if url_name.endswith("_excel") else "reports.view"

    if url_name.startswith("program_"):
        if "approve" in url_name:
            return "program.approve_challan"
        if "inward" in url_name:
            return "program.inward"
        if "challan" in url_name:
            return "program.challan"
        if "start" in url_name:
            return "program.start"
        if "costing" in url_name:
            return "program.costing"
        if "verify" in url_name:
            return "program.verify"
        if any(token in url_name for token in ("add", "create")):
            return "program.add"
        if any(token in url_name for token in ("edit", "update", "toggle")):
            return "program.edit"
        if "delete" in url_name:
            return "program.delete"
        return "program.view"

    if url_name.startswith("quality_check"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete")):
            return "qc.manage"
        return "qc.view"

    if url_name.startswith("qr_code"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "scan", "delete")):
            return "qr.manage"
        return "qr.view"

    if url_name.startswith("costing_snapshot"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete")):
            return "costing.manage"
        return "costing.view"

    if url_name.startswith("inventory_lot") or url_name == "stock_lot_wise":
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete")):
            return "inventory.manage"
        return "inventory.view"

    if url_name.startswith("dispatch"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete")):
            return "dispatch.manage"
        return "dispatch.view"

    if url_name.startswith("invoice"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete")):
            return "invoice.manage"
        return "invoice.view"

    if url_name.startswith("maintenance"):
        if any(token in url_name for token in ("add", "create", "edit", "update", "delete", "payload")):
            return "maintenance.manage"
        return "maintenance.view"

    if url_name.startswith("greigepo"):
        if "review" in url_name:
            return "greige_po.review"
        if "inward" in url_name:
            return "greige_po.inward"
        if "pdf" in url_name:
            return "greige_po.pdf"
        if any(token in url_name for token in ("add", "create")):
            return "greige_po.add"
        if any(token in url_name for token in ("edit", "update")):
            return "greige_po.edit"
        if "delete" in url_name:
            return "greige_po.delete"
        return "greige_po.view"

    if url_name.startswith("dyeingpo"):
        if "review" in url_name:
            return "dyeing_po.review"
        if "inward" in url_name:
            return "dyeing_po.inward"
        if "pdf" in url_name:
            return "dyeing_po.pdf"
        if any(token in url_name for token in ("add", "create")):
            return "dyeing_po.add"
        if any(token in url_name for token in ("edit", "update")):
            return "dyeing_po.edit"
        if "delete" in url_name:
            return "dyeing_po.delete"
        return "dyeing_po.view"

    if url_name.startswith("readypo"):
        if "review" in url_name:
            return "ready_po.review"
        if "inward" in url_name:
            return "ready_po.inward"
        if "pdf" in url_name:
            return "ready_po.pdf"
        if any(token in url_name for token in ("add", "create")):
            return "ready_po.add"
        if any(token in url_name for token in ("edit", "update")):
            return "ready_po.edit"
        if "delete" in url_name:
            return "ready_po.delete"
        return "ready_po.view"

    for prefix in MASTER_URL_PREFIXES:
        if url_name.startswith(prefix):
            if any(token in url_name for token in ("add", "create")):
                return "master.add"
            if any(token in url_name for token in ("edit", "update")):
                return "master.edit"
            if "delete" in url_name:
                return "master.delete"
            return "master.view"

    return ""


def get_actor(request):
    return getattr(request, "erp_actor", None) or getattr(request, "user", None)


def get_company(request):
    return getattr(request, "erp_company", None)


def get_user_profile(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.erp_profile
    except Exception:
        return None


def is_platform_admin(user):
    return bool(user and getattr(user, "is_authenticated", False) and user.is_superuser)


def is_company_admin(request_or_user):
    if hasattr(request_or_user, "erp_is_company_admin"):
        return bool(request_or_user.erp_is_company_admin)

    user = request_or_user
    if is_platform_admin(user):
        return False
    profile = get_user_profile(user)
    return bool(
        profile
        and profile.is_active
        and getattr(profile.user, "is_active", True)
        and profile.company
        and profile.company.is_active_company
        and profile.is_company_admin
    )


def get_permission_codes_for_actor(actor):
    if not actor or not getattr(actor, "is_authenticated", False):
        return set()

    if actor.is_superuser:
        return set(PLATFORM_ADMIN_PERMISSION_CODES)

    profile = get_user_profile(actor)
    if not profile:
        return set()

    if not getattr(actor, "is_active", True):
        return set()
    if not profile.is_active or not profile.company or not profile.company.is_active_company:
        return set()

    if profile.is_company_admin:
        return set(COMPANY_ADMIN_PERMISSION_CODES)

    role = profile.role
    if not role or not role.is_active:
        return set()

    return set(role.permissions or []) - STAFF_BLOCKED_PERMISSION_CODES


def has_erp_permission(request, code):
    if not code:
        return True

    actor = get_actor(request)
    if not actor or not getattr(actor, "is_authenticated", False):
        return False

    return code in get_permission_codes_for_actor(actor)


def can_see_sidebar_item(request, item):
    actor = get_actor(request)

    if item.get("platform_only") and not is_platform_admin(actor):
        return False
    if item.get("company_only") and is_platform_admin(actor):
        return False
    if item.get("company_admin_only") and not is_company_admin(request):
        return False
    if item.get("admin_only") and not (is_company_admin(request) or is_platform_admin(actor)):
        return False

    any_permissions = item.get("any_permissions") or []
    if any_permissions:
        return any(has_erp_permission(request, code) for code in any_permissions)

    url_name = item.get("url_name") or ""
    permission = item.get("permission") or SIDEBAR_PERMISSION_BY_URL_NAME.get(url_name)
    if not permission and url_name.startswith("accounts:"):
        permission = permission_for_url_name(url_name.split(":", 1)[1])
    return has_erp_permission(request, permission)


def actor_allowed_firm_ids(request):
    actor = get_actor(request)
    profile = get_user_profile(actor)
    if not actor or not getattr(actor, "is_authenticated", False):
        return []
    if actor.is_superuser or not profile or profile.is_company_admin:
        return None
    firm_ids = list(profile.allowed_firms.values_list("id", flat=True))
    return firm_ids


def actor_has_firm_access(request, firm_id):
    """Return True when the real login actor may access a firm.

    None from actor_allowed_firm_ids means unrestricted company-level access.
    An empty list means staff has not been assigned any firm yet.
    For restricted staff, records without a firm are not visible because there
    is no safe firm assignment to compare against.
    """
    firm_ids = actor_allowed_firm_ids(request)
    if firm_ids is None:
        return True
    if not firm_id:
        return False
    return int(firm_id) in set(int(pk) for pk in firm_ids)


def filter_queryset_by_actor_firms(request, queryset, firm_field="firm_id"):
    """Reusable helper for Part 3/4 firm enforcement.

    Example: qs = filter_queryset_by_actor_firms(request, qs, "firm_id")
    Use relation paths with Django's double-underscore style when needed.
    """
    firm_ids = actor_allowed_firm_ids(request)
    if firm_ids is None:
        return queryset
    return queryset.filter(**{f"{firm_field}__in": firm_ids})
