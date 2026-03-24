# Mise HERo Finance

Czech-language financial transaction management for Mise HERo organization.
Django 5.2 REST API + vanilla JS frontend.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+

### Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note:** Django does NOT auto-load `.env`. Set `POSTGRES_PASSWORD` manually:

```bash
export POSTGRES_PASSWORD=your_password  # or use inline: POSTGRES_PASSWORD=x python manage.py ...
```

```bash
python manage.py migrate
python manage.py seed_lookups
python manage.py createsuperuser
python manage.py runserver            # API at http://localhost:8000
```

Frontend (separate terminal):

```bash
cd frontend_demo && python -m http.server 5173  # http://localhost:5173
```

See `docs/DEV_SETUP.md` for full local development guide.

## API Endpoints

All endpoints require JWT auth: `POST /api/v1/auth/token/` with `{email, password}` → `{access, refresh}`.

| Area | Key Endpoints |
|------|---------------|
| Auth | `/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`, `/api/v1/auth/me/` |
| Transactions | `/api/v1/transactions/`, `{id}/`, `stats/`, `trends/`, `export/`, `bulk_update/`, `create-manual/` |
| Import | `/api/v1/imports/upload/`, `/api/v1/imports/upload-idoklad/`, `/api/v1/imports/` |
| Rules | `/api/v1/category-rules/`, `{id}/test/`, `apply_to_uncategorized/` |
| Lookups | `/api/v1/projects/`, `/api/v1/products/`, `/api/v1/subgroups/`, `/api/v1/cost-details/` |
| Users | `/api/v1/users/` (admin) |

## Project Structure

```
HeroWizzard_version2/
├── config/                  # Django settings, urls, wsgi
├── apps/
│   ├── core/                # User model (email-based), JWT auth, audit log
│   ├── transactions/        # Transactions, CSV import, category rules, lookups
│   ├── analytics/           # Placeholder (not implemented)
│   └── predictions/         # Placeholder (not implemented)
├── frontend_demo/           # Production frontend (static HTML/JS/CSS, no build step)
├── frontend/                # Unused React skeleton (scheduled for removal)
├── deploy/                  # Deploy script with auto-rollback
├── docs/                    # Documentation
└── .claude/                 # Claude Code skills and config
```

## User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access, Django admin panel, user management |
| `manager` | Import, edit, manage rules, approve transactions |
| `accountant` | Edit/categorize transactions, export |
| `viewer` | Read-only |

## Testing

```bash
pytest                                      # all tests
pytest apps/transactions/tests/ -v          # transaction tests
pytest --cov=apps --cov-report=term-missing # with coverage
```

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/DEV_SETUP.md` | Local development setup |
| `docs/USER_GUIDE.md` | End-user feature guide |
| `docs/CATEGORY_RULES.md` | Auto-categorization rule system spec |
| `docs/CSV_IMPORT_GUIDE.md` | CSV import formats and processing |
| `docs/DEPLOYMENT.md` | Infrastructure and deploy procedures |
| `docs/UPGRADE_GUIDE.md` | Version history and upgrade process |
| `CLAUDE.md` | Claude Code instruction set |

## License

Proprietary - Mise HERo © 2024
