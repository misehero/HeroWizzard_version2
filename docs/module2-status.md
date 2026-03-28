# Module 2 — Current Status

**Last updated:** 2026-03-28 (rename `frontend_demo/` → `frontend/` deployed to all 3 environments)

## Completed: Phase 1 (Foundation)

### What exists

- **9 models** in `apps/projects/` — Organization, PersonType, Person, ClientCategory, Client, AresCache, DealType, DealStatus, BudgetCategory
- **CRUD API** for all models under `/api/v1/m2/`
- **ARES integration** — `POST /api/v1/m2/ares/lookup/` with 30-day cache
- **Správa dat page** (`sprava-dat-m2.html`) with 10 editable tables, sidebar navigation, ARES button on clients
- **Seed data** — 4 organizations (MH, MHE, MHX, MHI), 3 person types, 6 client categories, 6 deal types, 8 deal statuses, 13 budget categories, 9 persons, 43 products, 40 budget templates
- **Tests** — model tests + API tests + service tests (37 total)
- **Navbar integration** — "Správa dat" link in Module 2 dropdown (admin-only)

### Seed command

```bash
python manage.py seed_module2_lookups
```

## Completed: Phase 2a (Products, Templates, Deals — Backend)

### New additions

- **5 new models** — ProductCatalog, BudgetLineTemplate, Deal, DealBudgetLine, DealPersonAssignment
- **Deal CRUD API** under `/api/v1/m2/deals/` with custom actions: `summary/`, `apply-template/`, `recalculate/`
- **ProductCatalog API** — `/api/v1/m2/products/` (paginated, filterable by deal_type)
- **BudgetLineTemplate API** — `/api/v1/m2/budget-templates/` (filterable by deal_type, category)
- **DealBudgetLine & DealPersonAssignment APIs** — full CRUD with filtering
- **DealService** — business logic for template application, calculation rules (`revenue_pct:N`), totals recalculation
- **Seed data** — 43 products (21 school + 22 corporate), 40 budget templates (all 6 deal types)

### Key features

- **Auto-template on deal creation** — creating a deal auto-copies BudgetLineTemplates into DealBudgetLines
- **Calculation rules** — `revenue_pct:N` automatically calculates budget line amounts as % of revenue
- **Organization split validation** — Deal.organization_split JSONField must sum to 100 or be empty
- **Unique person assignment** — UniqueConstraint prevents duplicate person→deal assignments
- **Deal filtering** — by deal_type, status, client, organization, owner, date range, search

## Completed: Phase 2b (Frontend — Zakázky + Přehled)

### New pages

- **`deals.html`** — "Zakázky a projekty" page
  - Filter bar: typ, stav, kvartál, firma, datum od/do, fulltext search
  - Deal table with colored type dots, status badges, financial columns
  - Pagination (50/page)
  - Click-to-expand deal detail modal with budget breakdown, person assignments
  - **"Nová zakázka" modal**: deal type selector, client picker, ARES lookup, budget template auto-fill, product-to-revenue mapping, person assignment with day rate calculation, organization split
- **`prehled-m2.html`** — "Přehled rozpočtu" dashboard
  - 4 summary cards: počet realizací, fakturováno, nefakturováno, celkem příjmy
  - Toggle between "Pohled: Zakázky" and "Pohled: Realizace" views
  - Same filter bar as deals page
  - Aggregates data across all pages for summary cards

### Navbar integration

- Module 2 dropdown now shows: Přehled | Zakázky | IDoklady | Správa dat (admin)

## What does NOT exist yet (do not assume these are built)

- No iDoklad section functionality (stub page only — `idoklady.html` is a placeholder)
- No HubSpot integration
- Transaction model has NOT been modified (no `idoklad_invoice` FK yet)
- No Excel export from deals page (placeholder button)
- No annual budget / yearly planning view

## Completed: Backup v8

Backup system bumped to **v8** (was v7). Now includes all 13 Module 2 business models:

**Phase 1 (v7):** Organization, PersonType, Person, ClientCategory, Client, DealType, DealStatus, BudgetCategory

**Phase 2a (v8 new):** ProductCatalog, BudgetLineTemplate, Deal, DealBudgetLine, DealPersonAssignment

AresCache is excluded (it's a cache, not business data).

Backward compatibility: importing a v3–v7 backup gracefully skips missing v8 keys.

## Next Steps (not started)

1. iDoklad VS matching (linking invoices to bank transactions)
2. Deal Excel export
3. Annual budget planning view
