"""Section-organized view exports backed by the legacy monolith."""

from ..views_legacy import (
    _first_form_error,
    _is_embed,
    _template_exists,
    _pick_template,
    _model_has_fields,
    _flatten_form_errors,
    _flatten_formset_errors,
    signup_view,
    login_view,
    logout_view,
    dashboard_view,
    utilities_view,
    developer_stats_view,
    profile_save,
    firm_save,
    notifications_mark_all_read,
)

__all__ = [
    "_first_form_error",
    "_is_embed",
    "_template_exists",
    "_pick_template",
    "_model_has_fields",
    "_flatten_form_errors",
    "_flatten_formset_errors",
    "signup_view",
    "login_view",
    "logout_view",
    "dashboard_view",
    "utilities_view",
    "developer_stats_view",
    "profile_save",
    "firm_save",
    "notifications_mark_all_read",
]
