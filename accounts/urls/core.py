from django.urls import path

from .. import views

urlpatterns = [
    path("platform/companies/", views.platform_company_list, name="platform_company_list"),
    path("platform/companies/add/", views.platform_company_create, name="platform_company_create"),
    path("platform/companies/<int:pk>/edit/", views.platform_company_update, name="platform_company_update"),
    path("platform/companies/<int:pk>/toggle/", views.platform_company_toggle, name="platform_company_toggle"),

    path("settings/roles/", views.role_list, name="role_list"),
    path("settings/roles/add/", views.role_create, name="role_create"),
    path("settings/roles/<int:pk>/edit/", views.role_update, name="role_update"),
    path("settings/roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("settings/users/add/", views.team_user_create, name="team_user_create"),
    path("settings/users/<int:pk>/edit/", views.team_user_update, name="team_user_update"),
    path("settings/users/<int:pk>/toggle/", views.team_user_toggle, name="team_user_toggle"),
    path("system/health/", views.system_health_view, name="system_health"),
    path("system/activity/", views.activity_log_view, name="activity_log"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("utilities/", views.utilities_view, name="utilities"),
    path("dev/stats/", views.developer_stats_view, name="developer_stats"),
    path("profile/save/", views.profile_save, name="profile_save"),
    path("firm/save/", views.firm_save, name="firm_save"),
    path("notifications/mark-all-read/", views.notifications_mark_all_read, name="notifications_mark_all_read"),
]
