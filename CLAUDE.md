# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mise HERo Finance - A Django REST API for managing financial transactions for the Mise HERo organization. The application handles CSV bank statement imports, transaction categorization with auto-detection rules, and multi-tribe (KMEN) expense splitting.

## Common Commands

```bash
# Development server
python manage.py runserver

# Run all tests
pytest

# Run single test file
pytest apps/transactions/tests/test_transactions.py

# Run tests with coverage
pytest --cov=apps --cov-report=html

# Skip slow tests
pytest -m "not slow"

# Linting
black --check apps/ config/
isort --check-only apps/ config/
flake8 apps/ config/

# Format code
black apps/ config/
isort apps/ config/

# Database
python manage.py migrate
python manage.py seed_lookups
python manage.py createsuperuser

# Makefile shortcuts available (make help for full list)
make test
make lint
make format
make run
```

## Architecture

### Django Apps (Modular Monolith)

- **apps/core/** - User model (email-based auth), JWT authentication, audit logging, permissions
- **apps/transactions/** - Main business logic: Transaction CRUD, CSV import, category rules, lookup tables
- **apps/analytics/** - Reports (placeholder for future)
- **apps/predictions/** - ML forecasting (placeholder for future)

### Key Models (apps/transactions/models.py)

**Transaction** - Central model with two field groups:
- 22 Bank Columns: Imported from CSV, mostly `editable=False` (datum, ucet, castka, cislo_protiuctu, nazev_merchanta, etc.)
- 14 App Columns: User-managed categorization (status, prijem_vydaj, vlastni_nevlastni, dane, druh, detail, kmen, mh/sk/xp/fr_pct, projekt, produkt, podskupina)

**CategoryRule** - Auto-detection rules with match hierarchy:
1. Protiucet (counterparty account number) - highest priority
2. Merchant name
3. Keyword (regex/contains/exact on message fields)

**Lookup tables**: Project, Product, ProductSubgroup, CostDetail

### CSV Import Service (apps/transactions/services.py)

`TransactionImporter` handles:
- **Auto-detection** of bank format (Raiffeisen vs generic)
- Czech CSV format (semicolon delimiter, comma decimal, DD.MM.YYYY dates)
- Raiffeisen Bank specific format with datetime parsing (DD.MM.YYYY HH:MM)
- Column mapping from Czech headers to model fields
- Duplicate detection via `id_transakce`
- Auto-detection rule application during import
- Batch tracking for audit

**Supported Bank Formats:**
- `GENERIC_CSV_MAPPING` - Standard Czech bank format (headers: Datum, Účet, Částka, etc.)
- `RAIFFEISEN_CSV_MAPPING` - Raiffeisen Bank format (headers: Datum provedení, Zaúčtovaná částka, Název obchodníka, etc.)

Format detection is automatic based on CSV headers (`detect_csv_format()` method).

### User Roles

admin, manager, accountant, viewer - defined in `apps/core/models.py:User.Role`

## API Structure

Base URL: `/api/v1/`

- `/auth/` - JWT token endpoints (login, refresh, me)
- `/transactions/` - Transaction CRUD + bulk_update, stats, trends, export
- `/imports/` - CSV upload and batch management
- `/category-rules/` - Rule CRUD + test/apply endpoints
- `/projects/`, `/products/`, `/subgroups/`, `/cost-details/` - Lookup endpoints

## Testing

Uses pytest-django with factory_boy. Key fixtures in `conftest.py`:
- `api_client`, `authenticated_client`, `admin_client`
- `user`, `admin_user`

Factories in `apps/transactions/tests/factories.py`:
- `TransactionFactory`, `CategorizedTransactionFactory`, `SplitTransactionFactory`
- `CategoryRuleFactory`, `ProjectFactory`, `ProductFactory`

## Czech Localization

- Language: Czech (cs), Timezone: Europe/Prague
- CSV format: Semicolon delimiter, Czech number format (1 234,56)
- Date format: DD.MM.YYYY
- Field names/choices use Czech terminology (Příjem/Výdaj, Vlastní/Nevlastní, etc.)

## KMEN Split Validation

Transactions have percentage fields (mh_pct, sk_pct, xp_pct, fr_pct) that must sum to exactly 100% or all be 0. Validated in `Transaction.clean()` and enforced by database constraint.

## Git Workflow & Rules

### Branch Strategy
- **main** - production-ready code, never commit directly
- **develop** - integration branch for features
- Feature branches: `feat/description` (e.g., `feat/csv-import-creditas`)
- Bugfix branches: `fix/description` (e.g., `fix/transaction-validation`)
- Refactor branches: `refactor/description`

### Commit Rules
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Write commit messages in English
- Keep commits atomic - one logical change per commit
- Always show me the full diff before committing
- Never commit secrets, .env files, API keys, or tokens

### Safety Rules
- **Never force push** (`git push --force` is forbidden)
- **Never push directly to main** - always use feature branches
- **Never commit without showing me the diff first**
- **Never run git reset --hard** without explicit approval
- Always check `git status` before committing
- Always check `git diff --staged` before pushing

### Workflow
1. Before starting work: `git checkout develop && git pull`
2. Create feature branch: `git checkout -b feat/feature-name`
3. Make changes and show diff for review
4. Commit with conventional message
5. Push feature branch: `git push -u origin feat/feature-name`
6. I will create the PR manually on GitHub
