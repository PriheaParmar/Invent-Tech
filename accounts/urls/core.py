from django.urls import path

from .. import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("utilities/", views.utilities_view, name="utilities"),
    path("dev/stats/", views.developer_stats_view, name="developer_stats"),
    path("profile/save/", views.profile_save, name="profile_save"),
    path("firm/save/", views.firm_save, name="firm_save"),
    path("notifications/mark-all-read/", views.notifications_mark_all_read, name="notifications_mark_all_read"),
]
