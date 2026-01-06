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

    # Jobbers (Master)
    path("master/jobbers/", views.jobber_list, name="jobber_list"),
    path("master/jobbers/add/", views.jobber_create, name="jobber_add"),
    path("master/jobbers/<int:pk>/edit/", views.jobber_update, name="jobber_edit"),
    path("master/jobbers/<int:pk>/delete/", views.jobber_delete, name="jobber_delete"),

    # Jobber Types
    path("master/jobber-types/", views.jobbertype_list_create, name="jobbertype_list"),

    # Optional alias URL (if you want Jobbers also under utilities)
    path("utilities/jobbers/", views.jobber_list, name="utilities_jobber_list"),
    
    path("master/materials/", views.material_list, name="material_list"),
    path("master/materials/add/", views.material_create, name="material_create"),
    path("master/materials/<int:pk>/edit/", views.material_edit, name="material_edit"),
    path("master/materials/<int:pk>/delete/", views.material_delete, name="material_delete"),
    
    path("master/parties/", views.party_list, name="party_list"),
    path("master/parties/add/", views.party_create, name="party_add"),
    path("master/parties/<int:pk>/edit/", views.party_update, name="party_edit"),
    path("master/parties/<int:pk>/delete/", views.party_delete, name="party_delete"),
    
    path("master/locations/", views.location_list, name="location_list"),
    path("master/locations/add/", views.location_create, name="location_add"),
    path("master/locations/<int:pk>/edit/", views.location_update, name="location_edit"),
    path("master/locations/<int:pk>/delete/", views.location_delete, name="location_delete"),
    
    path("master/firms/", views.firm_list, name="firm_list"),
    path("master/firms/add/", views.firm_create, name="firm_add"),
    path("master/firms/<int:pk>/edit/", views.firm_update, name="firm_edit"),
    path("master/firms/<int:pk>/delete/", views.firm_delete, name="firm_delete"),

    # optional legacy alias (if you already linked to /master/firm/)
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

]

