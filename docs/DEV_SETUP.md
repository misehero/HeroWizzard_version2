# Local Development & Testing Guide

---

## Prerequisites

- **Python 3.11+** (`python --version`)
- **PostgreSQL 14+** running on localhost:5432
- **Git**

---

## Step 1: Database Setup

```sql
-- In psql or pgAdmin:
CREATE DATABASE mise_hero_finance;
```

Note your PostgreSQL password for the `postgres` user.

---

## Step 2: Environment Variables

**Important:** Django does NOT auto-load `.env`. You must set env vars before running.

The only variable that likely differs from defaults is `POSTGRES_PASSWORD`:

**PowerShell:** `$env:POSTGRES_PASSWORD = "admin"`
**CMD:** `set POSTGRES_PASSWORD=admin`
**Bash:** `export POSTGRES_PASSWORD=admin`
**Inline:** `POSTGRES_PASSWORD=admin python manage.py runserver`

Other defaults from `config/settings.py`: DB=`mise_hero_finance`, USER=`postgres`, HOST=`localhost`, PORT=`5432`.

---

## Step 3: Install & Migrate

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_lookups       # projects, products, cost details
python manage.py createsuperuser    # email + password (min 8 chars)
```

---

## Step 4: Start Backend

```bash
python manage.py runserver
```

Backend at **http://localhost:8000**. Verify: http://localhost:8000/api/v1/

---

## Step 5: Start Frontend

Static files in `frontend_demo/`. Must serve via HTTP (not file://) for CORS.

```bash
cd frontend_demo && python -m http.server 5173
```

Frontend at **http://localhost:5173**. This origin is in CORS_ALLOWED_ORIGINS.

| URL | Page |
|-----|------|
| http://localhost:5173/index.html | Login |
| http://localhost:5173/dashboard.html | Dashboard |
| http://localhost:5173/upload.html | Import CSV |
| http://localhost:5173/categories.html | Category Rules |

---

## Manual Testing Scenarios

### Test 1: Import Creditas CSV

1. Import CSV → Creditas card → upload `docs/test-data/test_creditas.csv`
2. **Expected:** Total: 5, Imported: 5, Skipped: 0, Errors: 0

### Test 2: Import Raiffeisen CSV

1. Import CSV → Raiffeisen card → upload `docs/test-data/test_raiffeisen.csv`
2. **Expected:** Total: 5, Imported: 5
3. **Duplicate test:** Upload same file again → Expected: Imported: 0, Skipped: 5

### Test 3: Edit Transaction

1. Dashboard → pencil icon → verify bank fields are greyed out
2. Change Druh, KMEN, MH% → Save → verify persisted

### Test 4: Create Manual Transaction

1. Dashboard → + Přidat transakci → fill Date + Amount (-5000) → Save
2. **Expected:** P/V auto-set to V, Status = Upraveno (admin) or Čeká na schválení (accountant)

### Test 5: Category Rules

1. Categories → + Přidat pravidlo → Merchant/Contains/"test value" → Save
2. Click "Použít pravidla na nezařazené" → verify count

---

## Running Automated Tests

```bash
pytest                                         # all tests
pytest apps/transactions/tests/ -v             # transaction tests
pytest -x -q                                   # stop on first failure
pytest --cov=apps --cov-report=term-missing    # with coverage
pytest -m "not slow"                           # skip slow tests
```

### Test Fixtures (conftest.py)

`api_client`, `user`, `admin_user`, `authenticated_client`, `admin_client`

---

## Sample Data Files

Located in `docs/test-data/`:

| File | Format | Rows |
|------|--------|------|
| test_creditas.csv | Creditas | 5 |
| test_raiffeisen.csv | Raiffeisen | 5 |
| test_idoklad.csv | iDoklad | 5 |
| sample_raiffeisen.csv | Raiffeisen | 10 |

---

## API Quick Reference

```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpass"}'

# Use: -H "Authorization: Bearer <access_token>"
```

Key endpoints: see README.md API table.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "password authentication failed" | Check `POSTGRES_PASSWORD` matches your PG installation password |
| CORS error on frontend | Backend must be on :8000, frontend served via HTTP (not file://) on :5173 |
| "Login failed" | Verify backend running at :8000, check superuser credentials |
| Import shows all errors | Check CSV format matches expected bank format, try re-saving as UTF-8 |
| "Relation does not exist" | Run `python manage.py migrate` |
| Tests fail with connection errors | Ensure PostgreSQL running + `POSTGRES_PASSWORD` set |
| `psycopg2` install fails (Windows) | Install Visual C++ Build Tools, then `pip install psycopg2-binary` |
| "python: command not found" | Add Python to PATH or use full path |
| Port 8000 in use | `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F`, or use different port |
| PowerShell: venv activate denied | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Git line ending issues | `git config --global core.autocrlf true` |
