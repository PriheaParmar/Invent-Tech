from copy import deepcopy

from django.urls import NoReverseMatch, reverse


RAW_SIDEBAR_GROUPS = [
    {
        "label": "Main",
        "items": [
            {"label": "Dashboard", "url_name": "accounts:dashboard", "icon": "home"},
            {
                "label": "Utilities",
                "url_name": "accounts:utilities",
                "icon": "settings",
                "match_prefixes": ["/utilities/", "/master/"],
            },
        ],
    },
{
    "label": "Operations",
    "items": [
        {
            "label": "Procurement",
            "url_name": "accounts:po_home",
            "icon": "po",
            "match_prefixes": ["/po/"],
        },
        {
            "label": "Production",
            "url_name": "accounts:program_list",
            "icon": "production",
            "match_prefixes": ["/production/"],
        },
        {
            "label": "Reports",
            "url_name": "accounts:reports_home",
            "icon": "document",
            "match_prefixes": ["/reports/"],
            "match_url_names": [
                "reports_home",
                "report_jobber_type_wise",
                "report_jobber_type_wise_excel",
                "report_program_production",
                "report_program_production_excel",
            ],
        },
        {
            "label": "Inventory",
            "url_name": "accounts:stock_lot_wise",
            "icon": "inventory",
            "match_prefixes": ["/inventory/stock-lot-wise/"],
        },
        {
            "label": "Dispatch",
            "url_name": "accounts:dispatch_list",
            "icon": "dispatch",
            "match_prefixes": ["/dispatch/"],
        },
        {
            "label": "Invoices",
            "url_name": "accounts:invoice_list",
            "icon": "invoice",
            "match_prefixes": ["/sales/invoices/"],
        },
    ],
},
    {
        "label": "Quality & Control",
        "items": [
            {
                "label": "QC Register",
                "url_name": "accounts:quality_check_list",
                "icon": "quality",
                "match_prefixes": ["/qc/"],
            },
            {
                "label": "Lot Register",
                "url_name": "accounts:inventory_lot_list",
                "icon": "lot",
                "match_prefixes": ["/inventory/lots/"],
            },
            {
                "label": "Add QR Label",
                "url_name": "accounts:qr_code_add",
                "icon": "qr",
                "match_prefixes": ["/qr/"],
            },
            {
                "label": "Costing",
                "url_name": "accounts:costing_snapshot_list",
                "icon": "costing",
                "match_prefixes": ["/costing/"],
            },
        ],
    },
    {
        "label": "Admin",
        "items": [
            {
                "label": "Maintenance",
                "url_name": "accounts:maintenance_list",
                "icon": "maintenance",
                "match_prefixes": ["/maintenance/"],
            },
        ],
    },
]


RAW_UTILITIES_GROUPS = [
    {
        "title": "Master Setup",
        "description": "Core records that drive purchases, production, and stock movement.",
        "columns": 4,
        "items": [
            {"title": "Jobbers", "subtitle": "Create and manage worker or contractor records.", "url_name": "accounts:jobber_list", "icon": "jobber"},
            {"title": "Jobber Types", "subtitle": "Define reusable jobber categories.", "url_name": "accounts:jobbertype_list", "icon": "jobber-type"},
            {"title": "Materials", "subtitle": "Maintain yarn, greige, finished, and trim masters.", "url_name": "accounts:material_list", "icon": "material"},
            {"title": "Material Types", "subtitle": "Define material type masters by kind.", "url_name": "accounts:materialtype_list", "icon": "layers"},
            {"title": "Material Sub Types", "subtitle": "Link reusable sub types under each material type.", "url_name": "accounts:materialsubtype_list", "icon": "layers"},
            {"title": "Material Shades", "subtitle": "Maintain reusable shades and codes.", "url_name": "accounts:materialshade_list", "icon": "palette"},
            {"title": "Material Units", "subtitle": "Define purchase and stock measurement units.", "url_name": "accounts:materialunit_list", "icon": "scale"},
            {"title": "Accessories", "subtitle": "Maintain accessory and trim references.", "url_name": "accounts:accessory_list", "icon": "tag"},
            {"title": "Parties", "subtitle": "Maintain customer and business party records.", "url_name": "accounts:party_list", "icon": "party"},
            {"title": "Clients", "subtitle": "Maintain client records used across operations.", "url_name": "accounts:client_list", "icon": "client"},
            {"title": "Vendors", "subtitle": "Manage supplier and vendor master data.", "url_name": "accounts:vendor_list", "icon": "vendor"},
            {"title": "Locations", "subtitle": "Define plant, warehouse, and delivery locations.", "url_name": "accounts:location_list", "icon": "location"},
            {"title": "Brands", "subtitle": "Manage reusable customer and garment brand names.", "url_name": "accounts:brand_list", "icon": "badge"},
            {"title": "Categories", "subtitle": "Manage category structure for finished products.", "url_name": "accounts:category_list", "icon": "folder"},
            {"title": "Main Categories", "subtitle": "Maintain top-level catalogue grouping.", "url_name": "accounts:maincategory_list", "icon": "folder-tree"},
            {"title": "Sub Categories", "subtitle": "Maintain second-level product grouping.", "url_name": "accounts:subcategory_list", "icon": "folder-tree"},
        ],
    },
    {
        "title": "Planning & Design",
        "description": "Product planning masters that support BOM and production setup.",
        "columns": 3,
        "items": [
            {"title": "BOM", "subtitle": "Build bills of materials for production planning.", "url_name": "accounts:bom_list", "icon": "bom"},
            {"title": "Catalogue", "subtitle": "Manage catalogue and wear type records.", "url_name": "accounts:catalogue_list", "icon": "book"},
            {"title": "Pattern Types", "subtitle": "Maintain reusable pattern type references.", "url_name": "accounts:patterntype_list", "icon": "grid"},
        ],
    },
    {
        "title": "Operations Setup",
        "description": "Configuration used in inward, dyeing, and downstream transaction flows.",
        "columns": 3,
        "items": [
            {"title": "Dyeing Master", "subtitle": "Link vendors with greige materials and dyeing options.", "url_name": "accounts:dyeing_material_link_list", "icon": "droplet"},
            {"title": "Dyeing Other Charges", "subtitle": "Maintain reusable dyeing extra charge rows.", "url_name": "accounts:dyeing_other_charge_list", "icon": "receipt"},
            {"title": "Inward Types", "subtitle": "Define reusable inward type classifications.", "url_name": "accounts:inwardtype_list", "icon": "inward"},
            {"title": "Terms & Conditions", "subtitle": "Maintain reusable commercial terms for documents.", "url_name": "accounts:termscondition_list", "icon": "document"},
        ],
    },
    {
        "title": "Accounts & Controls",
        "description": "Administrative setup that supports costing and control records.",
        "columns": 2,
        "items": [
            {"title": "Expenses", "subtitle": "Maintain reusable expense heads and costing inputs.", "url_name": "accounts:expense_list", "icon": "wallet"},
        ],
    },
]


ICON_CLASS_MAP = {
    "jobber": "icon-jobber",
    "jobber-type": "icon-jobber-type",
    "material": "icon-material",
}


def _clone_groups(groups):
    return deepcopy(groups)


def _resolve_url(url_name):
    if not url_name:
        return ""
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return ""


def _normalize_prefix(prefix):
    if not prefix:
        return ""
    return prefix if prefix.endswith("/") else f"{prefix}/"


def _is_active(request_path, current_url_name, item, resolved_url):
    prefixes = [_normalize_prefix(prefix) for prefix in item.get("match_prefixes", []) if prefix]
    if resolved_url:
        prefixes.append(_normalize_prefix(resolved_url))

    for prefix in prefixes:
        if prefix and request_path.startswith(prefix):
            return True

    match_names = item.get("match_url_names", [])
    return bool(current_url_name and current_url_name in match_names)


def _resolve_groups(raw_groups, request):
    request_path = request.path or ""
    current_url_name = getattr(getattr(request, "resolver_match", None), "url_name", "") or ""

    groups = []
    for raw_group in _clone_groups(raw_groups):
        items = []
        for raw_item in raw_group.get("items", []):
            resolved_url = _resolve_url(raw_item.get("url_name"))
            item = {
                **raw_item,
                "url": resolved_url or "#",
                "icon_css_class": ICON_CLASS_MAP.get(raw_item.get("icon"), ""),
                "is_disabled": not bool(resolved_url),
                "is_active": _is_active(request_path, current_url_name, raw_item, resolved_url),
            }
            item["search_text"] = " ".join(
                filter(
                    None,
                    [
                        raw_item.get("title"),
                        raw_item.get("label"),
                        raw_item.get("subtitle"),
                        raw_group.get("title"),
                        raw_group.get("description"),
                    ],
                )
            ).lower()
            items.append(item)

        group = {
            **raw_group,
            "items": items,
            "count": len(items),
            "has_active": any(item["is_active"] for item in items),
        }
        groups.append(group)
    return groups


def get_sidebar_groups(request):
    return _resolve_groups(RAW_SIDEBAR_GROUPS, request)


def get_utility_groups(request):
    return _resolve_groups(RAW_UTILITIES_GROUPS, request)