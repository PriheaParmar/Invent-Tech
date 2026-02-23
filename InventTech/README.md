# InventTech (Django)

This repo is a Django project (currently centered around the `accounts` app) that includes:
- Authentication (signup/login/logout)
- Dashboard + utilities pages
- Master data CRUD: Jobbers, Jobber Types, Materials, Parties, Locations, Firms, Material Types/Shades
- Media uploads (Material images)

## Quick start (Windows / Linux / macOS)

### 1) Create & activate a virtual environment
```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
Copy `.env.example` to `.env` and set values:
```bash
cp .env.example .env
```

### 4) Run migrations + start server
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:
- http://127.0.0.1:8000/login/
- http://127.0.0.1:8000/admin/

## Notes / recommended cleanup
- Don’t commit `.venv/`, `db.sqlite3`, or `media/` to git (they’re already in `.gitignore`).
- `config/settings.py` reads secrets from `.env` (no extra package needed).
- `static/` exists for global static assets; app-level static remains in `accounts/static/`.

## UI / CSS structure (updated)

Shared UI styles are now split for easier maintenance:

- `accounts/static/css/core.css` → shared app layout/components (loaded by `base_app.html`)
- `accounts/static/css/modules/` → module-level styles (jobbers/materials/parties)
- `accounts/static/css/pages/` → per-page CSS files (each page links its own file)
- `accounts/static/css/auth/core.css` → shared auth styles (loaded by `base.html`)

If you want to style a specific screen, start in:
- `css/pages/<screen>.css` (and import a module if needed)

## Next improvements (typical)
- Split “ERP modules” into separate Django apps (masters, inventory, sales, etc.)
- Add tests + CI (GitHub Actions)
- Add Docker + Postgres for production
- Add permissions/roles, audit logs, exports, etc.
