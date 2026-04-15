from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # =========================================================
    # Auth
    # =========================================================
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # =========================================================
    # Main Pages
    # =========================================================
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("utilities/", views.utilities_view, name="utilities"),
    path("dev/stats/", views.developer_stats_view, name="developer_stats"),
    path("profile/save/", views.profile_save, name="profile_save"),
    path("firm/save/", views.firm_save, name="firm_save"),

    # =========================================================
    # Inventory / Reports
    # =========================================================
    path("inventory/stock-lot-wise/", views.stock_lot_wise, name="stock_lot_wise"),

    # =========================================================
    # Master - Jobbers
    # =========================================================
    path("master/jobbers/", views.jobber_list, name="jobber_list"),
    path("master/jobbers/add/", views.jobber_create, name="jobber_add"),
    path("master/jobbers/<int:pk>/edit/", views.jobber_update, name="jobber_edit"),
    path("master/jobbers/<int:pk>/delete/", views.jobber_delete, name="jobber_delete"),

    # Jobber Types
    path("master/jobber-types/", views.jobbertype_list_create, name="jobbertype_list"),
    path("master/jobber-types/<int:pk>/edit/", views.jobbertype_edit, name="jobbertype_edit"),
    path("master/jobber-types/<int:pk>/delete/", views.jobbertype_delete, name="jobbertype_delete"),

    # Optional alias URL
    path("utilities/jobbers/", views.jobber_list, name="utilities_jobber_list"),

    # =========================================================
    # Master - Materials
    # =========================================================
    path("master/materials/", views.material_list, name="material_list"),
    path("master/materials/select-kind/", views.material_kind_picker, name="material_kind_picker"),
    path("master/materials/add/", views.material_create, name="material_create"),
    path("master/materials/<int:pk>/edit/", views.material_edit, name="material_edit"),
    path("master/materials/<int:pk>/delete/", views.material_delete, name="material_delete"),

    # Material Shades
    path("utilities/material-shades/", views.materialshade_list, name="materialshade_list"),
    path("utilities/material-shades/add/", views.materialshade_create, name="materialshade_add"),
    path("utilities/material-shades/<int:pk>/edit/", views.materialshade_update, name="materialshade_edit"),
    path("utilities/material-shades/<int:pk>/delete/", views.materialshade_delete, name="materialshade_delete"),

    # Material Types
    path("utilities/material-types/", views.materialtype_list, name="materialtype_list"),
    path("utilities/material-types/add/", views.materialtype_create, name="materialtype_add"),
    path("utilities/material-types/<int:pk>/edit/", views.materialtype_update, name="materialtype_edit"),
    path("utilities/material-types/<int:pk>/delete/", views.materialtype_delete, name="materialtype_delete"),

    # Material Sub Types
    path("utilities/material-sub-types/", views.materialsubtype_list, name="materialsubtype_list"),
    path("utilities/material-sub-types/add/", views.materialsubtype_create, name="materialsubtype_add"),
    path("utilities/material-sub-types/<int:pk>/edit/", views.materialsubtype_update, name="materialsubtype_edit"),
    path("utilities/material-sub-types/<int:pk>/delete/", views.materialsubtype_delete, name="materialsubtype_delete"),

    # Material Units
    path("utilities/material-units/", views.materialunit_list_create, name="materialunit_list"),
    path("utilities/material-units/<int:pk>/edit/", views.materialunit_edit, name="materialunit_edit"),
    path("utilities/material-units/<int:pk>/delete/", views.materialunit_delete, name="materialunit_delete"),

    # Accessories
    path("utilities/accessories/", views.accessory_list_create, name="accessory_list"),
    path("utilities/accessories/<int:pk>/edit/", views.accessory_edit, name="accessory_edit"),
    path("utilities/accessories/<int:pk>/delete/", views.accessory_delete, name="accessory_delete"),

    # =========================================================
    # Master - Parties / Vendors / Locations / Firm / Clients
    # =========================================================
    path("master/parties/", views.party_list, name="party_list"),
    path("master/parties/add/", views.party_create, name="party_add"),
    path("master/parties/<int:pk>/edit/", views.party_update, name="party_edit"),
    path("master/parties/<int:pk>/delete/", views.party_delete, name="party_delete"),

    path("master/locations/", views.location_list, name="location_list"),
    path("master/locations/add/", views.location_create, name="location_add"),
    path("master/locations/<int:pk>/edit/", views.location_update, name="location_edit"),
    path("master/locations/<int:pk>/delete/", views.location_delete, name="location_delete"),

    path("master/vendors/", views.vendor_list, name="vendor_list"),
    path("master/vendors/add/", views.vendor_create, name="vendor_add"),
    path("master/vendors/<int:pk>/edit/", views.vendor_update, name="vendor_edit"),
    path("master/vendors/<int:pk>/delete/", views.vendor_delete, name="vendor_delete"),

    path("firm/", views.firm_view, name="firm"),
    path("firms/", views.firm_list, name="firm_list"),
    path("firms/add/", views.firm_create, name="firm_add"),
    path("firms/<int:pk>/edit/", views.firm_update, name="firm_edit"),
    path("firms/<int:pk>/delete/", views.firm_delete, name="firm_delete"),

    path("master/clients/", views.client_list, name="client_list"),
    path("master/clients/add/", views.client_create, name="client_add"),
    path("master/clients/<int:pk>/edit/", views.client_update, name="client_edit"),
    path("master/clients/<int:pk>/delete/", views.client_delete, name="client_delete"),

    # =========================================================
    # Master / Utilities - Catalogue / Category / Branding
    # =========================================================
    path("master/brands/", views.brand_list, name="brand_list"),
    path("master/brands/add/", views.brand_create, name="brand_add"),
    path("master/brands/<int:pk>/edit/", views.brand_update, name="brand_edit"),
    path("master/brands/<int:pk>/delete/", views.brand_delete, name="brand_delete"),

    path("master/categories/", views.category_list, name="category_list"),
    path("master/categories/add/", views.category_create, name="category_add"),
    path("master/categories/<int:pk>/edit/", views.category_update, name="category_edit"),
    path("master/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    path("utilities/catalogues/", views.catalogue_list, name="catalogue_list"),
    path("utilities/catalogues/add/", views.catalogue_create, name="catalogue_add"),
    path("utilities/catalogues/<int:pk>/edit/", views.catalogue_update, name="catalogue_edit"),
    path("utilities/catalogues/<int:pk>/delete/", views.catalogue_delete, name="catalogue_delete"),

    path("utilities/main-categories/", views.maincategory_list, name="maincategory_list"),
    path("utilities/main-categories/add/", views.maincategory_create, name="maincategory_add"),
    path("utilities/main-categories/<int:pk>/edit/", views.maincategory_edit, name="maincategory_edit"),
    path("utilities/main-categories/<int:pk>/delete/", views.maincategory_delete, name="maincategory_delete"),

    path("utilities/sub-categories/", views.subcategory_list, name="subcategory_list"),
    path("utilities/sub-categories/add/", views.subcategory_create, name="subcategory_add"),
    path("utilities/sub-categories/<int:pk>/edit/", views.subcategory_edit, name="subcategory_edit"),
    path("utilities/sub-categories/<int:pk>/delete/", views.subcategory_delete, name="subcategory_delete"),

    path("utilities/pattern-types/", views.patterntype_list_create, name="patterntype_list"),
    path("utilities/pattern-types/<int:pk>/edit/", views.patterntype_edit, name="patterntype_edit"),
    path("utilities/pattern-types/<int:pk>/delete/", views.patterntype_delete, name="patterntype_delete"),

    # =========================================================
    # Utilities - Expenses / Terms / Charges / Inward / BOM
    # =========================================================
    path("utilities/expenses/", views.expense_list_create, name="expense_list"),
    path("utilities/expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("utilities/expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),

    path("utilities/terms-conditions/", views.termscondition_list, name="termscondition_list"),
    path("utilities/terms-conditions/add/", views.termscondition_create, name="termscondition_add"),
    path("utilities/terms-conditions/<int:pk>/edit/", views.termscondition_update, name="termscondition_edit"),
    path("utilities/terms-conditions/<int:pk>/delete/", views.termscondition_delete, name="termscondition_delete"),

    path("utilities/dyeing-other-charges/", views.dyeing_other_charge_list, name="dyeing_other_charge_list"),
    path("utilities/dyeing-other-charges/add/", views.dyeing_other_charge_create, name="dyeing_other_charge_add"),
    path("utilities/dyeing-other-charges/<int:pk>/edit/", views.dyeing_other_charge_edit, name="dyeing_other_charge_edit"),
    path("utilities/dyeing-other-charges/<int:pk>/delete/", views.dyeing_other_charge_delete, name="dyeing_other_charge_delete"),

    path("utilities/inward-types/", views.inwardtype_list, name="inwardtype_list"),
    path("utilities/inward-types/add/", views.inwardtype_create, name="inwardtype_add"),
    path("utilities/inward-types/<int:pk>/edit/", views.inwardtype_edit, name="inwardtype_edit"),
    path("utilities/inward-types/<int:pk>/delete/", views.inwardtype_delete, name="inwardtype_delete"),

    path("utilities/bom/", views.bom_list, name="bom_list"),
    path("utilities/bom/add/", views.bom_create, name="bom_add"),
    path("utilities/bom/<int:pk>/edit/", views.bom_update, name="bom_edit"),
    path("utilities/bom/<int:pk>/delete/", views.bom_delete, name="bom_delete"),

    path("utilities/dyeing-material-links/", views.dyeing_material_link_list, name="dyeing_material_link_list"),
    path("utilities/dyeing-material-links/add/", views.dyeing_material_link_create, name="dyeing_material_link_add"),
    path("utilities/dyeing-material-links/<int:pk>/edit/", views.dyeing_material_link_update, name="dyeing_material_link_edit"),
    path("utilities/dyeing-material-links/<int:pk>/delete/", views.dyeing_material_link_delete, name="dyeing_material_link_delete"),

    # =========================================================
    # PO Home
    # =========================================================
    path("po/", views.po_home, name="po_home"),

    # =========================================================
    # Yarn Purchase Orders
    # =========================================================
    path("po/yarn/", views.yarnpo_list, name="yarnpo_list"),
    path("po/yarn/add/", views.yarnpo_create, name="yarnpo_add"),
    path("po/yarn/<int:pk>/edit/", views.yarnpo_update, name="yarnpo_edit"),
    path("po/yarn/<int:pk>/delete/", views.yarnpo_delete, name="yarnpo_delete"),
    path("po/yarn/<int:pk>/review/", views.yarnpo_review, name="yarnpo_review"),
    path("po/yarn/<int:pk>/pdf/", views.yarnpo_pdf, name="yarnpo_pdf"),
    path("po/yarn/<int:pk>/inward/", views.yarnpo_inward, name="yarnpo_inward"),
    path("po/yarn/inwards/<int:pk>/edit/", views.yarn_inward_update, name="yarn_inward_edit"),
    path("po/yarn/inwards/", views.yarn_inward_tracker, name="yarn_inward_tracker"),
    path("po/yarn/<int:pk>/generate-greige/", views.generate_greige_po_from_yarn, name="generate_greige_po_from_yarn"),

    # =========================================================
    # Greige Purchase Orders
    # =========================================================
    path("po/greige/", views.greigepo_list, name="greigepo_list"),
    path("po/greige/add/", views.greigepo_create, name="greigepo_add"),
    path("po/greige/add/from-yarn/<int:yarn_po_id>/", views.greigepo_create, name="greigepo_add_from_yarn"),
    path("po/greige/<int:pk>/", views.greigepo_detail, name="greigepo_detail"),
    path("po/greige/<int:pk>/edit/", views.greigepo_update, name="greigepo_edit"),
    path("po/greige/<int:pk>/delete/", views.greigepo_delete, name="greigepo_delete"),
    path("po/greige/<int:pk>/review/", views.greigepo_review, name="greigepo_review"),
    path("po/greige/<int:pk>/pdf/", views.greigepo_pdf, name="greigepo_pdf"),
    path("po/greige/<int:pk>/inward/", views.greigepo_inward, name="greigepo_inward"),
    path("po/greige/inwards/<int:pk>/edit/", views.greige_inward_edit, name="greige_inward_edit"),
    path("po/greige/inwards/", views.greige_inward_tracker, name="greige_inward_tracker"),
    path("po/greige/<int:pk>/generate-dyeing/", views.generate_dyeing_po_from_greige, name="generate_dyeing_po_from_greige"),

    # =========================================================
    # Dyeing Purchase Orders
    # =========================================================
    path("po/dyeing/", views.dyeingpo_list, name="dyeingpo_list"),
    path("po/dyeing/add/", views.dyeingpo_create, name="dyeingpo_add"),
    path("po/dyeing/add/from-greige/<int:greige_po_id>/", views.dyeingpo_create, name="dyeingpo_add_from_greige"),
    path("po/dyeing/<int:pk>/", views.dyeingpo_detail, name="dyeingpo_detail"),
    path("po/dyeing/<int:pk>/edit/", views.dyeingpo_update, name="dyeingpo_edit"),
    path("po/dyeing/<int:pk>/delete/", views.dyeingpo_delete, name="dyeingpo_delete"),
    path("po/dyeing/<int:pk>/review/", views.dyeingpo_review, name="dyeingpo_review"),
    path("po/dyeing/<int:pk>/inward/", views.dyeingpo_inward, name="dyeingpo_inward"),
    path("po/dyeing/inwards/<int:pk>/edit/", views.dyeing_inward_edit, name="dyeing_inward_edit"),
    path("po/dyeing/inwards/", views.dyeing_inward_tracker, name="dyeing_inward_tracker"),
    path("po/dyeing/<int:pk>/generate-ready/", views.generate_ready_po_from_dyeing, name="generate_ready_po_from_dyeing"),
    path("po/dyeing/<int:pk>/review/", views.dyeingpo_review, name="dyeingpo_review"),

    # =========================================================
    # Ready Purchase Orders
    # =========================================================
    path("po/ready/", views.readypo_list, name="readypo_list"),
    path("po/ready/add/", views.readypo_create, name="readypo_add"),
    path("po/ready/add/from-dyeing/<int:dyeing_po_id>/", views.readypo_create, name="readypo_add_from_dyeing"),
    path("po/ready/<int:pk>/", views.readypo_detail, name="readypo_detail"),
    path("po/ready/<int:pk>/edit/", views.readypo_update, name="readypo_edit"),
    path("po/ready/<int:pk>/delete/", views.readypo_delete, name="readypo_delete"),
    path("po/ready/<int:pk>/inward/", views.readypo_inward, name="readypo_inward"),
    path("po/ready/inwards/<int:pk>/edit/", views.ready_inward_edit, name="ready_inward_edit"),
    path("po/ready/inwards/", views.ready_inward_tracker, name="ready_inward_tracker"),

    # =========================================================
    # Production Programs
    # =========================================================
    path("production/programs/", views.program_list, name="program_list"),
    path("production/programs/add/", views.program_create, name="program_add"),
    path("production/programs/<int:pk>/edit/", views.program_update, name="program_edit"),
    path("production/programs/<int:pk>/verify-toggle/", views.program_toggle_verify, name="program_toggle_verify"),
    path("production/programs/<int:pk>/status-toggle/", views.program_toggle_status, name="program_toggle_status"),
    path("production/programs/<int:pk>/print/", views.program_print, name="program_print"),

    # =========================================================
    # Dispatch / Challan
    # =========================================================
    path("dispatch/", views.dispatch_list, name="dispatch_list"),
    path("dispatch/programs/", views.dispatch_program_picker, name="dispatch_program_picker"),
    path("dispatch/create/<int:program_id>/", views.dispatch_create, name="dispatch_create"),
    path("dispatch/<int:pk>/", views.dispatch_detail, name="dispatch_detail"),
    path("dispatch/<int:pk>/print/", views.dispatch_print, name="dispatch_print"),
]
