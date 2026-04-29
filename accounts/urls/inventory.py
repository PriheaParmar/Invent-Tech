from django.urls import path

from .. import views

urlpatterns = [
    path("inventory/stock-lot-wise/", views.stock_lot_wise, name="stock_lot_wise"),
    path("inventory/lots/", views.inventory_lot_list, name="inventory_lot_list"),
    path("inventory/lots/<int:pk>/", views.inventory_lot_detail, name="inventory_lot_detail"),
    path("qc/", views.quality_check_list, name="quality_check_list"),
    path("qc/add/", views.quality_check_create, name="quality_check_add"),
    path("qc/<int:pk>/", views.quality_check_detail, name="quality_check_detail"),
    path("qr/add/", views.qr_code_create, name="qr_code_add"),
    path("qr/<int:pk>/", views.qr_code_detail, name="qr_code_detail"),
    path("costing/", views.costing_snapshot_list, name="costing_snapshot_list"),
    path("costing/add/", views.costing_snapshot_create, name="costing_snapshot_add"),
    path("qr/scan/<str:code>/", views.qr_code_scan, name="qr_code_scan"),
]
