from django.urls import path

from .. import views

urlpatterns = [
    path("maintenance/", views.maintenance_list, name="maintenance_list"),
    path("maintenance/add/", views.maintenance_create, name="maintenance_add"),
    path("maintenance/month-payload/", views.maintenance_month_payload, name="maintenance_month_payload"),
]
