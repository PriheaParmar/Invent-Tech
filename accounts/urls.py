from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Main pages
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("utilities/", views.utilities_view, name="utilities"),
    path("dev/stats/", views.developer_stats_view, name="developer_stats"),
    path("profile/save/", views.profile_save, name="profile_save"),
    path("firm/save/", views.firm_save, name="firm_save"),

    # Jobbers (Master)
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

    # Materials
    path("master/materials/", views.material_list, name="material_list"),
    path("master/materials/select-kind/", views.material_kind_picker, name="material_kind_picker"),
    path("master/materials/add/", views.material_create, name="material_create"),
    path("master/materials/<int:pk>/edit/", views.material_edit, name="material_edit"),
    path("master/materials/<int:pk>/delete/", views.material_delete, name="material_delete"),

    # Parties
    path("master/parties/", views.party_list, name="party_list"),
    path("master/parties/add/", views.party_create, name="party_add"),
    path("master/parties/<int:pk>/edit/", views.party_update, name="party_edit"),
    path("master/parties/<int:pk>/delete/", views.party_delete, name="party_delete"),

    # Locations
    path("master/locations/", views.location_list, name="location_list"),
    path("master/locations/add/", views.location_create, name="location_add"),
    path("master/locations/<int:pk>/edit/", views.location_update, name="location_edit"),
    path("master/locations/<int:pk>/delete/", views.location_delete, name="location_delete"),

    # Firms
    path("master/firms/", views.firm_list, name="firm_list"),
    path("master/firms/add/", views.firm_create, name="firm_add"),
    path("master/firms/<int:pk>/edit/", views.firm_update, name="firm_edit"),
    path("master/firms/<int:pk>/delete/", views.firm_delete, name="firm_delete"),

    # Optional legacy alias
    path("master/firm/", views.firm_list, name="firm"),

    # Material Shades
    path("master/material-shades/", views.materialshade_list, name="materialshade_list"),
    path("master/material-shades/add/", views.materialshade_create, name="materialshade_add"),
    path("master/material-shades/<int:pk>/edit/", views.materialshade_update, name="materialshade_edit"),
    path("master/material-shades/<int:pk>/delete/", views.materialshade_delete, name="materialshade_delete"),

    # Material Types
    path("master/material-types/", views.materialtype_list, name="materialtype_list"),
    path("master/material-types/add/", views.materialtype_create, name="materialtype_add"),
    path("master/material-types/<int:pk>/edit/", views.materialtype_update, name="materialtype_edit"),
    path("master/material-types/<int:pk>/delete/", views.materialtype_delete, name="materialtype_delete"),

    # Vendor master
    path("master/vendors/", views.vendor_list, name="vendor_list"),
    path("master/vendors/add/", views.vendor_create, name="vendor_add"),
    path("master/vendors/<int:pk>/edit/", views.vendor_update, name="vendor_edit"),
    path("master/vendors/<int:pk>/delete/", views.vendor_delete, name="vendor_delete"),

   # Purchase Orders
    path("po/", views.po_home, name="po_home"),

    # Yarn Purchase Orders
    path("po/yarn/", views.yarnpo_list, name="yarnpo_list"),
    path("po/yarn/add/", views.yarnpo_create, name="yarnpo_add"),
    path("po/yarn/<int:pk>/edit/", views.yarnpo_update, name="yarnpo_edit"),
    path("po/yarn/<int:pk>/delete/", views.yarnpo_delete, name="yarnpo_delete"),
    path("po/yarn/<int:pk>/review/", views.yarnpo_review, name="yarnpo_review"),
    path("po/yarn/<int:pk>/pdf/", views.yarnpo_pdf, name="yarnpo_pdf"),
    path("po/yarn/<int:pk>/inward/", views.yarnpo_inward, name="yarnpo_inward"),
    path("po/yarn/inwards/", views.yarn_inward_tracker, name="yarn_inward_tracker"),
    path("po/yarn/<int:pk>/generate-greige/", views.generate_greige_po_from_yarn, name="generate_greige_po_from_yarn"),

    # Greige Purchase Orders
    path("po/greige/", views.greigepo_list, name="greigepo_list"),
    path("po/greige/add/", views.greigepo_create, name="greigepo_add"),
    path("po/greige/add/from-yarn/<int:yarn_po_id>/", views.greigepo_create, name="greigepo_add_from_yarn"),
    path("po/greige/<int:pk>/", views.greigepo_detail, name="greigepo_detail"),
    path("po/greige/<int:pk>/edit/", views.greigepo_update, name="greigepo_edit"),
    path("po/greige/<int:pk>/delete/", views.greigepo_delete, name="greigepo_delete"),
    path("po/greige/<int:pk>/inward/", views.greigepo_inward, name="greigepo_inward"),
    path("po/greige/inwards/", views.greige_inward_tracker, name="greige_inward_tracker"),
    path("po/greige/<int:pk>/generate-dyeing/", views.generate_dyeing_po_from_greige, name="generate_dyeing_po_from_greige"),

    # Dyeing Purchase Orders
    path("po/dyeing/", views.dyeingpo_list, name="dyeingpo_list"),
    path("po/dyeing/add/", views.dyeingpo_create, name="dyeingpo_add"),
    path("po/dyeing/add/from-greige/<int:greige_po_id>/", views.dyeingpo_create, name="dyeingpo_add_from_greige"),
    path("po/dyeing/<int:pk>/", views.dyeingpo_detail, name="dyeingpo_detail"),
]