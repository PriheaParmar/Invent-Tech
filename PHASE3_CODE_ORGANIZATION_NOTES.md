# Phase 3 Code Organization Cleanup Applied

This phase focuses on code organization only. Business logic, models, templates, and route behavior were intentionally preserved.

## What changed
- Converted `accounts.views` from a single file into an organized package backed by `accounts/views_legacy.py`.
- Converted `accounts.forms` from a single file into an organized package backed by `accounts/forms_legacy.py`.
- Converted `accounts.urls` from a single file into an organized package backed by section-based URL modules.

## New package layout
- `accounts/views/`
  - `core.py`
  - `masters.py`
  - `planning.py`
  - `procurement.py`
  - `production.py`
  - `inventory.py`
  - `sales.py`
  - `maintenance.py`
- `accounts/forms/`
  - `core.py`
  - `masters.py`
  - `planning.py`
  - `procurement.py`
  - `production.py`
  - `inventory.py`
  - `sales.py`
  - `maintenance.py`
- `accounts/urls/`
  - `auth.py`
  - `core.py`
  - `masters.py`
  - `planning.py`
  - `procurement.py`
  - `production.py`
  - `inventory.py`
  - `sales.py`
  - `maintenance.py`

## Compatibility approach
- Existing imports such as `from . import views` and `from .forms import ...` continue to work.
- Existing view logic remains in the legacy files for now to keep the refactor low-risk.
- The new packages re-export the same public API so section-by-section work can continue without changing URLs or templates.

## Not changed
- Models and migrations
- Business rules
- Templates and static assets
- PO / inward / program flow behavior
- PDF generation behavior

## Next recommended step
- Start moving business logic out of `views_legacy.py` into true section modules and services one section at a time, beginning with the section you want to improve first.
