# Local Development & Testing Guide

Quick-start guide for running Mise HERo Finance locally on Windows and testing all features.

---

## Prerequisites

- **Python 3.11+** (verify: `python --version`)
- **PostgreSQL 14+** running on localhost:5432
- **Git** (optional, for cloning)

---

## Step 1: Database Setup

Create the PostgreSQL database. Use pgAdmin or command line:

```sql
-- In psql or pgAdmin query tool:
CREATE DATABASE mise_hero_finance;
```

Note your PostgreSQL password for the `postgres` user (set during PG installation).

---

## Step 2: Environment Variables

**Important:** The `.env` file exists but Django does NOT auto-load it. You must set environment variables manually before running the server or tests.

### Option A: Set in terminal session (recommended)

**PowerShell:**
```powershell
$env:POSTGRES_PASSWORD = "admin"
$env:DJANGO_DEBUG = "True"
```

**CMD:**
```cmd
set POSTGRES_PASSWORD=admin
set DJANGO_DEBUG=True
```

**Git Bash / WSL:**
```bash
export POSTGRES_PASSWORD=admin
export DJANGO_DEBUG=True
```

### Option B: Inline with command

```bash
POSTGRES_PASSWORD=admin python manage.py runserver
```

The only variable that likely differs from defaults is `POSTGRES_PASSWORD`. Defaults used by `config/settings.py`:

| Variable | Default | Your `.env` value |
|----------|---------|-------------------|
| POSTGRES_DB | mise_hero_finance | mise_hero_finance |
| POSTGRES_USER | postgres | postgres |
| POSTGRES_PASSWORD | postgres | **admin** |
| POSTGRES_HOST | localhost | localhost |
| POSTGRES_PORT | 5432 | 5432 |

---

## Step 3: Install & Migrate

```bash
# Install dependencies (use venv if preferred)
pip install -r requirements.txt

# Run migrations
POSTGRES_PASSWORD=admin python manage.py migrate

# Seed lookup tables (projects, products, cost details)
POSTGRES_PASSWORD=admin python manage.py seed_lookups

# Create a superuser for login
POSTGRES_PASSWORD=admin python manage.py createsuperuser
```

When prompted for superuser:
- **Email:** e.g. `test@test.com`
- **Password:** e.g. `testtest1` (min 8 chars, not too common)

---

## Step 4: Start the Backend

```bash
POSTGRES_PASSWORD=admin python manage.py runserver
```

Backend runs at **http://localhost:8000**. Keep this terminal open.

Verify: open http://localhost:8000/api/v1/ in browser - should show API root JSON.

---

## Step 5: Start the Frontend

The frontend is a set of static HTML files in `frontend_demo/`. They call the API at `http://localhost:8000`. You need to serve them via HTTP (not file://) for CORS to work.

**Open a second terminal** and run:

```bash
cd frontend_demo
python -m http.server 5173
```

Frontend runs at **http://localhost:5173**. This origin is already allowed in CORS settings.

### Pages

| URL | Page |
|-----|------|
| http://localhost:5173/index.html | Login |
| http://localhost:5173/dashboard.html | Dashboard (transactions) |
| http://localhost:5173/upload.html | Import CSV |
| http://localhost:5173/categories.html | Category Rules |

---

## Step 6: Login

1. Open http://localhost:5173/index.html
2. Enter the superuser email and password you created in Step 3
3. On success, you are redirected to the Dashboard

---

## Manual Testing Scenarios

### Test 1: Import Creditas CSV

1. Go to **Import CSV** page (http://localhost:5173/upload.html)
2. In the **Creditas CSV** card, click the upload zone or drag `docs/test_creditas.csv`
3. Click **Upload & Import**
4. **Expected result:**
   - Total: 5
   - Imported: 5
   - Skipped: 0
   - Errors: 0
5. Go to Dashboard - 5 new transactions should appear
6. Verify first transaction: amount 15,000.00 CZK, account 118514285/2250

### Test 2: Import Raiffeisen CSV

1. Go to **Import CSV** page
2. In the **Raiffeisen CSV** card, upload `docs/test_raiffeisen.csv`
3. Click **Upload & Import**
4. **Expected result:**
   - Total: 5
   - Imported: 5
   - Skipped: 0
   - Errors: 0
5. Go to Dashboard - 5 more transactions (10 total)
6. **Duplicate test:** Upload `docs/test_raiffeisen.csv` again
7. **Expected:** Imported: 0, Skipped: 5 (Raiffeisen has transaction IDs for dedup)

### Test 3: Edit a Transaction

1. Go to **Dashboard**
2. Click the **pencil icon** on any transaction
3. The edit modal opens - note that bank fields (Date, Amount, etc.) are **greyed out / disabled**
4. Change editable fields:
   - Set **Status** to "Zpracovano"
   - Set **Druh** to "Fixni"
   - Set **KMEN** to "MH", set **MH%** to 100, others to 0
5. Click **Save**
6. **Expected:** Modal closes, transaction row updates with new values
7. Click edit again to verify values were persisted

### Test 4: Create a New Transaction

1. Go to **Dashboard**
2. Click **+ Add Transaction** button
3. Fill in:
   - **Date:** today's date
   - **Amount:** -5000
   - **Note:** "Test manual transaction"
   - **Counterparty:** "Test Company"
   - **Druh:** "Variabilni"
4. Click **Save**
5. **Expected:** New transaction appears in table with Status "Upraveno", P/V "V" (auto-set from negative amount)

### Test 5: Create a Category Rule

1. Go to **Categories** page (http://localhost:5173/categories.html)
2. Click **+ Add Rule**
3. Fill in:
   - **Name:** "Test Rule - Westernmarket"
   - **Match Type:** Merchant
   - **Match Mode:** Contains
   - **Match Value:** "Westernmarket"
   - **Set Druh:** "Variabilni"
   - **Set V/N:** Vlastni
4. Click **Save**
5. **Expected:** New rule appears in the rules table

### Test 6: Verify Rules Apply During Import

This tests the integration between Category Rules and CSV Import:

1. First create a rule (if not done in Test 5):
   - **Match Type:** Protiucet (Account Number)
   - **Match Mode:** Exact
   - **Match Value:** `987654321/1234`
   - **Set Druh:** "Projekt EU"
2. Delete existing Raiffeisen transactions (or use a fresh database)
3. Import `docs/test_raiffeisen.csv`
4. Go to Dashboard and find the transaction from Klient Alpha s.r.o. (counterparty 987654321/1234)
5. **Expected:** That transaction already has Druh = "Projekt EU" (auto-set by the rule during import)
6. Other transactions without matching rules should have empty Druh

### Test 7: Apply Rules to Existing Uncategorized Transactions

1. Go to **Categories** page
2. Ensure you have a rule that matches some existing transactions
3. Click **Apply Rules to Uncategorized**
4. **Expected:** Success message showing how many transactions were updated
5. Go to Dashboard to verify affected transactions now have the rule's values

---

## Running Automated Tests

Open a new terminal:

```bash
# Run all feature tests (30 tests)
POSTGRES_PASSWORD=admin python -m pytest apps/transactions/tests/test_feature_tests.py -v

# Run all tests in the project
POSTGRES_PASSWORD=admin python -m pytest -v

# Run with coverage
POSTGRES_PASSWORD=admin python -m pytest --cov=apps --cov-report=term-missing
```

### Test Summary

| Test Class | Count | What It Tests |
|-----------|-------|---------------|
| TestCreditasCSVImport | 4 | Upload, field mapping, auto P/V, batch creation |
| TestRaiffeisenCSVImport | 5 | Upload, field mapping, duplicate detection, auto P/V, Czech decimals |
| TestTransactionEditing | 6 | Status, categorization, KMEN validation, FK updates, readonly bank fields |
| TestManualTransactionCreation | 5 | Minimal/full create, auto P/V, validation errors |
| TestCategoryRuleCRUD | 5 | Create/update/delete rules, regex validation |
| TestCategoryRulesAppliedDuringImport | 5 | Rules applied during import, hierarchy, inactive rules |

---

## Sample Data Files

Located in `docs/`:

| File | Format | Rows | Description |
|------|--------|------|-------------|
| test_creditas.csv | Creditas | 5 | Test Creditas import (1 income, 4 expenses) |
| test_raiffeisen.csv | Raiffeisen | 5 | Test Raiffeisen import (2 income, 3 expenses) |
| test_idoklad.csv | iDoklad | 5 | Test iDoklad invoices (skip for now) |
| sample_raiffeisen.csv | Raiffeisen | 10 | Larger Raiffeisen sample |
| MHE_12-25-dummy.csv | Raiffeisen | ~20 | Dummy MHE data |
| MHX_12-25-dummy_creditas_bank.csv | Creditas | ~20 | Dummy Creditas data |

---

## API Quick Reference

All endpoints require JWT authentication. Get a token first:

```bash
# Login - get JWT token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testtest1"}'

# Use the access token in subsequent requests:
# -H "Authorization: Bearer <access_token>"
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/auth/token/ | POST | Login (email + password) |
| /api/v1/auth/token/refresh/ | POST | Refresh JWT token |
| /api/v1/transactions/ | GET | List transactions (paginated, filterable) |
| /api/v1/transactions/{id}/ | GET/PATCH | Get/update single transaction |
| /api/v1/transactions/create-manual/ | POST | Create transaction manually |
| /api/v1/transactions/stats/ | GET | Aggregated statistics |
| /api/v1/imports/upload/ | POST | Upload bank CSV (multipart) |
| /api/v1/imports/ | GET | List import batches |
| /api/v1/category-rules/ | GET/POST | List/create rules |
| /api/v1/category-rules/{id}/ | PATCH/DELETE | Update/delete rule |
| /api/v1/category-rules/apply_to_uncategorized/ | POST | Apply rules to uncategorized |
| /api/v1/projects/ | GET | List projects |
| /api/v1/products/ | GET | List products |

---

## Troubleshooting

### "password authentication failed for user postgres"

Your PostgreSQL password doesn't match. Check what password you set during PostgreSQL installation and use that:

```bash
POSTGRES_PASSWORD=your_actual_password python manage.py runserver
```

### Frontend shows CORS error

Make sure:
1. Backend is running on port 8000
2. Frontend is served via `python -m http.server 5173` (not opened as file://)
3. If using a different port, add it to CORS_ALLOWED_ORIGINS env var:
   ```bash
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080 python manage.py runserver
   ```

### "Login failed" on frontend

1. Verify backend is running: visit http://localhost:8000/api/v1/
2. Verify you created a superuser with `python manage.py createsuperuser`
3. Try logging in via curl to check credentials (see API Quick Reference above)

### Import shows 0 imported, all errors

Check the error details table below the import result. Common causes:
- CSV file is not in the expected format
- File encoding issue (try re-saving as UTF-8)

### "Relation does not exist" or migration errors

Run migrations:
```bash
POSTGRES_PASSWORD=admin python manage.py migrate
```

### Tests fail with connection errors

Ensure PostgreSQL is running and the password env var is set:
```bash
POSTGRES_PASSWORD=admin python -m pytest -v
```
