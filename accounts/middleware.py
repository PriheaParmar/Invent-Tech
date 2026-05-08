from django.shortcuts import render

from .permissions import has_erp_permission, permission_for_url_name
from .audit import clear_current_request, set_current_request, write_audit_log


class ERPTenantMiddleware:
    """
    Product-level tenant bridge.

    Existing ERP code filters data with owner=request.user. For staff users,
    this middleware keeps the real login user in request.erp_actor, then points
    request.user to the company admin/owner so legacy queries continue to read
    the correct company dataset without rewriting every view at once.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        request.erp_actor = user
        request.erp_owner = user
        request.erp_company = None
        request.erp_user_profile = None
        request.erp_is_company_admin = False
        request.erp_is_platform_admin = bool(user and getattr(user, "is_authenticated", False) and user.is_superuser)

        if user and getattr(user, "is_authenticated", False) and not user.is_superuser:
            try:
                profile = user.erp_profile
            except Exception:
                profile = None

            if profile:
                request.erp_user_profile = profile
                request.erp_company = profile.company
                request.erp_is_company_admin = bool(profile.is_company_admin)
                if profile.company and profile.company.admin_user_id:
                    request.erp_owner = profile.company.admin_user
                    # Legacy owner=request.user bridge.
                    request.user = profile.company.admin_user

        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        resolver_match = getattr(request, "resolver_match", None)
        url_name = getattr(resolver_match, "url_name", "") or ""

        # Auth/static/admin/default Django pages should stay outside ERP permission gate.
        if not url_name:
            return None
        if url_name in {"login", "logout", "signup", "password_reset", "password_reset_done", "password_reset_confirm", "password_reset_complete"}:
            return None
        if request.path.startswith("/admin/"):
            return None

        # Block suspended/inactive company access before individual URL rules.
        # This also protects legacy routes that do not yet have a permission code.
        actor = getattr(request, "erp_actor", None)
        profile = getattr(request, "erp_user_profile", None)
        if actor and getattr(actor, "is_authenticated", False) and not getattr(actor, "is_superuser", False):
            company = getattr(request, "erp_company", None)
            if (profile is None) or (not getattr(profile, "is_active", False)) or (not company) or (not company.is_active_company):
                return render(
                    request,
                    "accounts/permissions/forbidden.html",
                    {
                        "required_permission": "Active ERP company account",
                        "erp_actor": actor,
                    },
                    status=403,
                )

        permission = permission_for_url_name(url_name)

        # Platform super admin is intentionally limited to platform/system pages.
        # If a route has no permission mapping yet, do not let super admin fall
        # through into company ERP data by accident.
        if actor and getattr(actor, "is_authenticated", False) and getattr(actor, "is_superuser", False) and not permission:
            return render(
                request,
                "accounts/permissions/forbidden.html",
                {
                    "required_permission": "Mapped platform permission",
                    "erp_actor": actor,
                },
                status=403,
            )

        if permission and not has_erp_permission(request, permission):
            return render(
                request,
                "accounts/permissions/forbidden.html",
                {
                    "required_permission": permission,
                    "erp_actor": getattr(request, "erp_actor", None),
                },
                status=403,
            )
        return None


class AuditTrailMiddleware:
    """Stores current request for model signals and records failed pages/exceptions."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            response = self.get_response(request)
        except Exception as exc:
            if not self._skip_path(request):
                write_audit_log(
                    action="exception",
                    severity="error",
                    module="Runtime",
                    message=f"{exc.__class__.__name__}: {exc}",
                    status_code=500,
                    request=request,
                    extra={"exception_class": exc.__class__.__name__},
                )
            raise
        else:
            status_code = getattr(response, "status_code", None)
            if status_code and status_code >= 400 and not self._skip_path(request):
                write_audit_log(
                    action="http_error",
                    severity="error" if status_code >= 500 else "warning",
                    module="HTTP",
                    message=f"HTTP {status_code} on {getattr(request, 'path', '')}",
                    status_code=status_code,
                    request=request,
                )
            return response
        finally:
            clear_current_request()

    def _skip_path(self, request):
        path = getattr(request, "path", "") or ""
        return path.startswith("/static/") or path.startswith("/media/") or path.startswith("/favicon")
