from django.urls import path

from .. import views

urlpatterns = [
    path("dispatch/", views.dispatch_list, name="dispatch_list"),
    path("dispatch/programs/", views.dispatch_program_picker, name="dispatch_program_picker"),
    path("dispatch/create/<int:program_id>/", views.dispatch_create, name="dispatch_create"),
    path("dispatch/<int:pk>/", views.dispatch_detail, name="dispatch_detail"),
    path("dispatch/<int:pk>/print/", views.dispatch_print, name="dispatch_print"),

    path("sales/invoices/", views.invoice_list, name="invoice_list"),
    path("sales/invoices/add/", views.invoice_create, name="invoice_add"),
    path("sales/invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("sales/invoices/<int:pk>/print/", views.invoice_print, name="invoice_print"),
    path("sales/invoices/program-payload/<int:program_id>/", views.invoice_program_payload, name="invoice_program_payload"),
]
