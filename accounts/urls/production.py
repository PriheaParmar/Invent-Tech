from django.urls import path

from .. import views

urlpatterns = [
    path("production/programs/", views.program_list, name="program_list"),
    path("production/programs/add/", views.program_create, name="program_add"),
    path("production/programs/<int:pk>/edit/", views.program_update, name="program_edit"),
    path("production/programs/<int:pk>/verify/", views.program_verify, name="program_verify"),
    path("production/programs/<int:pk>/verify-toggle/", views.program_toggle_verify, name="program_toggle_verify"),
    path("production/programs/<int:pk>/status-toggle/", views.program_toggle_status, name="program_toggle_status"),
    path("production/programs/<int:pk>/print/", views.program_print, name="program_print"),
    path("production/programs/<int:pk>/start/", views.program_start_modal, name="program_start_modal"),
    path("production/programs/<int:pk>/start/save/", views.program_start_save, name="program_start_save"),
    path("production/programs/<int:program_id>/challans/", views.program_challan_manage, name="program_challan_manage"),
    path("production/programs/<int:program_id>/challans/create/<int:start_jobber_id>/", views.program_challan_create, name="program_challan_create"),
    path("production/program-challans/<int:pk>/", views.program_challan_detail, name="program_challan_detail"),
    path("production/program-challans/<int:pk>/approve/", views.program_challan_approve, name="program_challan_approve"),
    path("production/program-challans/<int:pk>/print/", views.program_challan_print, name="program_challan_print"),
    path("production/program-challans/<int:challan_id>/inward/", views.program_inward_form, name="program_inward_form"),
    path("production/programs/<int:program_id>/costing/", views.program_costing_detail, name="program_costing_detail"),
    path("reports/jobber-type-wise/", views.report_jobber_type_wise, name="report_jobber_type_wise"),
    path("reports/jobber-type-wise/excel/", views.report_jobber_type_wise_excel, name="report_jobber_type_wise_excel"),
    path("reports/", views.reports_home, name="reports_home"),
path("reports/program-production/", views.report_program_production, name="report_program_production"),
path("reports/program-production/excel/", views.report_program_production_excel, name="report_program_production_excel"),
path("reports/ready-fabric-po-details/", views.report_ready_fabric_po_details, name="report_ready_fabric_po_details"),
path("reports/ready-fabric-po-details/excel/", views.report_ready_fabric_po_details_excel, name="report_ready_fabric_po_details_excel"),
path("reports/stitching-inwards/", views.report_stitching_inwards, name="report_stitching_inwards"),
path("reports/stitching-inwards/excel/", views.report_stitching_inwards_excel, name="report_stitching_inwards_excel"),
path("reports/used-lot-details/", views.report_used_lot_details, name="report_used_lot_details"),
path("reports/used-lot-details/excel/", views.report_used_lot_details_excel, name="report_used_lot_details_excel"),
path("reports/program-stage-flow/", views.report_program_stage_flow, name="report_program_stage_flow"),
path("reports/program-stage-flow/excel/", views.report_program_stage_flow_excel, name="report_program_stage_flow_excel"),

path("reports/ready-po-status/", views.report_ready_po_status, name="report_ready_po_status"),
path("reports/ready-po-status/excel/", views.report_ready_po_status_excel, name="report_ready_po_status_excel"),

path("reports/inventory-lot-stock/", views.report_inventory_lot_stock, name="report_inventory_lot_stock"),
path("reports/inventory-lot-stock/excel/", views.report_inventory_lot_stock_excel, name="report_inventory_lot_stock_excel"),
path("reports/dyeing-po-status/", views.report_dyeing_po_status, name="report_dyeing_po_status"),
path("reports/dyeing-po-status/excel/", views.report_dyeing_po_status_excel, name="report_dyeing_po_status_excel"),

path("reports/greige-po-status/", views.report_greige_po_status, name="report_greige_po_status"),
path("reports/greige-po-status/excel/", views.report_greige_po_status_excel, name="report_greige_po_status_excel"),

path("reports/yarn-po-status/", views.report_yarn_po_status, name="report_yarn_po_status"),
path("reports/yarn-po-status/excel/", views.report_yarn_po_status_excel, name="report_yarn_po_status_excel"),
path("reports/dispatch-pending/", views.report_dispatch_pending, name="report_dispatch_pending"),
path("reports/dispatch-pending/excel/", views.report_dispatch_pending_excel, name="report_dispatch_pending_excel"),

path("reports/program-jobber/", views.report_program_jobber, name="report_program_jobber"),
path("reports/program-jobber/excel/", views.report_program_jobber_excel, name="report_program_jobber_excel"),

path("reports/used-lot-summary/", views.report_used_lot_summary, name="report_used_lot_summary"),
path("reports/used-lot-summary/excel/", views.report_used_lot_summary_excel, name="report_used_lot_summary_excel"),
]
