"""Section-organized view exports backed by the legacy monolith."""

from ..views_legacy import (
    _normalize_stock_lot_search_value,
    _build_stock_lot_rows_for_user,
    stock_lot_wise,
    _sync_phase2_lots_from_dyeing,
    inventory_lot_list,
    inventory_lot_detail,
    quality_check_create,
    quality_check_list,
    quality_check_detail,
    qr_code_create,
    qr_code_detail,
    qr_code_scan,
    costing_snapshot_list,
    costing_snapshot_create,
)

__all__ = [
    "_normalize_stock_lot_search_value",
    "_build_stock_lot_rows_for_user",
    "stock_lot_wise",
    "_sync_phase2_lots_from_dyeing",
    "inventory_lot_list",
    "inventory_lot_detail",
    "quality_check_create",
    "quality_check_list",
    "quality_check_detail",
    "qr_code_create",
    "qr_code_detail",
    "qr_code_scan",
    "costing_snapshot_list",
    "costing_snapshot_create",
]
