from django.urls import path

from .. import views

urlpatterns = [
    path("utilities/bom/", views.bom_list, name="bom_list"),
    path("utilities/bom/add/", views.bom_create, name="bom_add"),
    path("utilities/bom/<int:pk>/edit/", views.bom_update, name="bom_edit"),
    path("utilities/bom/<int:pk>/delete/", views.bom_delete, name="bom_delete"),
]
