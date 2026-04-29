"""Section-organized view exports backed by the legacy monolith."""

from ..views_legacy import (
    _dispatch_list_url,
    _dispatch_feature_available,
    _dispatch_feature_unavailable_response,
    dispatch_list,
    dispatch_program_picker,
    dispatch_create,
    dispatch_detail,
    _build_dispatch_challan_pdf_response,
    dispatch_print,
    _invoice_month_range,
    invoice_list,
    invoice_program_payload,
    invoice_create,
    invoice_detail,
    _build_program_invoice_pdf_response,
    invoice_print,
)

__all__ = [
    "_dispatch_list_url",
    "_dispatch_feature_available",
    "_dispatch_feature_unavailable_response",
    "dispatch_list",
    "dispatch_program_picker",
    "dispatch_create",
    "dispatch_detail",
    "_build_dispatch_challan_pdf_response",
    "dispatch_print",
    "_invoice_month_range",
    "invoice_list",
    "invoice_program_payload",
    "invoice_create",
    "invoice_detail",
    "_build_program_invoice_pdf_response",
    "invoice_print",
]
