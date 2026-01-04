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
]
