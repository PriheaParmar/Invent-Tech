"""Organized URL package assembled from section modules."""

from .auth import urlpatterns as auth_urlpatterns
from .core import urlpatterns as core_urlpatterns
from .inventory import urlpatterns as inventory_urlpatterns
from .maintenance import urlpatterns as maintenance_urlpatterns
from .masters import urlpatterns as masters_urlpatterns
from .planning import urlpatterns as planning_urlpatterns
from .procurement import urlpatterns as procurement_urlpatterns
from .production import urlpatterns as production_urlpatterns
from .sales import urlpatterns as sales_urlpatterns

app_name = "accounts"

urlpatterns = [
    *auth_urlpatterns,
    *core_urlpatterns,
    *inventory_urlpatterns,
    *masters_urlpatterns,
    *planning_urlpatterns,
    *procurement_urlpatterns,
    *production_urlpatterns,
    *sales_urlpatterns,
    *maintenance_urlpatterns,
]