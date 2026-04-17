APP_SIDEBAR_GROUPS = [
    {
        "label": "Workspace",
        "items": [
            {"label": "Dashboard", "url_name": "accounts:dashboard", "icon": "home"},
            {"label": "Utilities", "url_name": "accounts:utilities", "icon": "settings"},
            {"label": "PO", "url_name": "accounts:po_home", "icon": "po"},
            {"label": "Inventory", "url_name": None, "icon": "inventory", "is_placeholder": True},
            {"label": "Program", "url_name": "accounts:program_list", "icon": "production"},
            {"label": "Production", "url_name": None, "icon": "production", "is_placeholder": True},
            {"label": "Dispatch", "url_name": "accounts:dispatch_list", "icon": "dispatch"},
            {"label": "Invoices", "url_name": "accounts:invoice_list", "icon": "dispatch"},
            {"label": "Maintenance", "url_name": "accounts:maintenance_list", "icon": "settings"},
        ],
    },
    {
        "label": "Masters",
        "items": [
            {"label": "Material Master", "url_name": "accounts:material_list", "icon": "material"},
            {"label": "Parties", "url_name": "accounts:party_list", "icon": "party"},
            {"label": "Vendors", "url_name": "accounts:vendor_list", "icon": "party"},
            {"label": "Locations", "url_name": "accounts:location_list", "icon": "location"},
        ],
    },
    {
        "label": "Reports",
        "items": [
            {"label": "Reports", "url_name": None, "icon": "report", "is_placeholder": True},
            {"label": "Settings", "url_name": None, "icon": "settings", "trigger": "settings"},
        ],
    },
]


UTILITIES_GROUPS = [
    {
        "title": "Masters",
        "description": "Core setup data used across the ERP.",
        "items": [
            {
                "title": "Jobbers",
                "subtitle": "Create and manage worker or contractor records.",
                "url_name": "accounts:jobber_list",
                "kind": "embed",
            },
            {
                "title": "Jobber Types",
                "subtitle": "Define reusable jobber categories.",
                "url_name": "accounts:jobbertype_list",
                "kind": "embed",
            },
            {
                "title": "Materials",
                "subtitle": "Maintain yarn, greige, finished, and trim masters.",
                "url_name": "accounts:material_list",
                "kind": "embed",
            },
            {
                "title": "Material Types",
                "subtitle": "Define material type masters by kind.",
                "url_name": "accounts:materialtype_list",
                "kind": "embed",
            },
            {
                "title": "Material Sub Types",
                "subtitle": "Link reusable sub types under each material type.",
                "url_name": "accounts:materialsubtype_list",
                "kind": "embed",
            },
            {
                "title": "Material Shades",
                "subtitle": "Maintain reusable shades and codes.",
                "url_name": "accounts:materialshade_list",
                "kind": "embed",
            },
            {
                "title": "Parties",
                "subtitle": "Maintain customer and business party records.",
                "url_name": "accounts:party_list",
                "kind": "embed",
            },
            {
                "title": "Vendors",
                "subtitle": "Manage supplier and yarn vendor master data.",
                "url_name": "accounts:vendor_list",
                "kind": "embed",
            },
            {
                "title": "Dyeing Master",
                "subtitle": "Link vendors with greige materials and available dyeing options.",
                "url_name": "accounts:dyeing_material_link_list",
                "kind": "embed",
            },
            {
                "title": "Locations",
                "subtitle": "Define plant, warehouse, or delivery locations.",
                "url_name": "accounts:location_list",
                "kind": "embed",
            },
            {
                "title": "Firm Details",
                "subtitle": "View and update the active business entity profile.",
                "url_name": "accounts:firm_list",
                "kind": "embed",
            },
        ],
    },
            {
                "title": "Purchase Orders",
                "description": "Entry points for buying workflows and reviews.",
                "items": [
            {
                "title": "PO Home",
                "subtitle": "Central purchase order landing page.",
                "url_name": "accounts:po_home",
                "kind": "page",
            },
            {
                "title": "Yarn PO",
                "subtitle": "Create, review, and manage yarn purchase orders.",
                "url_name": "accounts:yarnpo_list",
                "kind": "page",
            },
            {
                "title": "Brands",
                "subtitle": "Manage reusable customer and garment brand names.",
                "url_name": "accounts:brand_list",
                "kind": "embed",
            },
            {
            "title": "Catalogue",
            "subtitle": "Manage catalogue and wear type records.",
            "url_name": "accounts:catalogue_list",
            "kind": "embed",
            },
            {
            "title": "Pattern Type",
            "subtitle": "....",
            "url_name": "accounts:patterntype_list",
            "kind": "embed",
        },
            
        ],
    },
]