# Category Rules (Pravidla kategorií)

Complete reference for the auto-detection rule system that automatically categorizes transactions during CSV import and on-demand.

## Overview

Category rules match transactions based on their bank-imported fields (account number, merchant, message, etc.) and automatically assign categorization fields (P/V, druh, detail, kmen, projekt, etc.). Rules are applied:

1. **During CSV import** — each imported transaction is matched against active rules before saving
2. **On-demand** — via the "Použít pravidla na nezařazené" button on the categories page

Only **one rule** is applied per transaction — the first match wins across the entire hierarchy.

---

## Match Type Hierarchy

Rules are evaluated in strict hierarchy order. If a match is found at a higher level, lower levels are skipped entirely.

| Priority | Match Type | Czech Name | Matches Against | Transaction Field |
|----------|------------|------------|-----------------|-------------------|
| 1 (highest) | `protiucet` | Protiúčet (Číslo účtu) | Counterparty account number | `cislo_protiuctu` |
| 2 | `merchant` | Název obchodníka | Merchant name from bank | `nazev_merchanta` |
| 3 | `vs` | Variabilní symbol | Variable symbol | `variabilni_symbol` |
| 4 | `typ` | Typ transakce | Transaction type | `typ` |
| 5 | `mesto` | Město | Merchant city | `mesto` |
| 6 (lowest) | `keyword` | Klíčové slovo | Message + notes combined | `poznamka_zprava` + `vlastni_poznamka` + `nazev_protiuctu` |

**Keyword special behavior:** For keyword match, three fields are concatenated with spaces and searched as one string: `poznamka_zprava`, `vlastni_poznamka`, and `nazev_protiuctu`.

### Priority Within Same Match Type

Within the same match type, rules are ordered by the `priority` field (lower number = higher priority). Default priority is 100. The first matching rule wins.

---

## Match Modes

Each rule has a match mode that determines how `match_value` is compared to the transaction field:

| Mode | Czech Name | Behavior |
|------|------------|----------|
| `exact` | Přesná shoda | Value must match exactly (default) |
| `contains` | Obsahuje | Value must appear anywhere in the field |
| `starts_with` | Začíná na | Field must start with the value |

**Case sensitivity:** By default, matching is case-insensitive (both sides lowercased). Enable `case_sensitive` for exact-case matching.

**Note:** Regex matching is NOT supported. All legacy references have been corrected.

---

## Fields a Rule Can Set

When a rule matches, it can set any combination of these transaction fields:

### Categorization Fields
| Rule Field | Transaction Field | Type | Notes |
|------------|-------------------|------|-------|
| `set_prijem_vydaj` | `prijem_vydaj` | CharField(1) | "P" (příjem) or "V" (výdaj) |
| `set_vlastni_nevlastni` | `vlastni_nevlastni` | CharField(1) | "V" (výnosy), "N" (náklady), or "-" |
| `set_dane` | `dane` | BooleanField | `null`=don't set, `true`=daňově relevantní |
| `set_druh` | `druh` | CharField(50) | Category/type (e.g. fixní, variabilní, mzdy) |
| `set_detail` | `detail` | CharField(200) | Detail description |
| `set_kmen` | `kmen` | CharField(2) | "MH", "SK", "XP", or "FR" |

### KMEN Split Percentages
| Rule Field | Transaction Field | Type |
|------------|-------------------|------|
| `set_mh_pct` | `mh_pct` | Decimal(5,2) |
| `set_sk_pct` | `sk_pct` | Decimal(5,2) |
| `set_xp_pct` | `xp_pct` | Decimal(5,2) |
| `set_fr_pct` | `fr_pct` | Decimal(5,2) |

### Lookup References (ForeignKey)
| Rule Field | Transaction Field | Model |
|------------|-------------------|-------|
| `set_projekt` | `projekt` | Project |
| `set_produkt` | `produkt` | Product |
| `set_podskupina` | `podskupina` | ProductSubgroup |

---

## Backend Architecture

### Model: `CategoryRule` (apps/transactions/models.py)

- UUID primary key
- DB table: `transactions_category_rule`
- Default ordering: `match_type`, `priority`, `name`
- Index on: `(match_type, is_active, priority)`
- Soft-delete via `is_active` field
- Audit: `created_at`, `updated_at`, `created_by`

### Service: `TransactionImporter` (apps/transactions/services.py)

Key methods:
- `apply_autodetection_rules(transaction)` — main entry point, walks the hierarchy
- `_load_caches()` — loads all active rules into memory grouped by match_type
- `_find_matching_rule(match_type, search_value)` — finds first match within a type
- `_rule_matches(rule, search_value)` — checks exact/contains/starts_with
- `_apply_rule_to_transaction(rule, transaction)` — copies rule settings to transaction

**Caching:** Rules are loaded once via `_load_caches()` into a dict keyed by match_type. Each value is a list of rules sorted by priority. This cache persists for the lifetime of the `TransactionImporter` instance.

### Serializer: `CategoryRuleSerializer` (apps/transactions/serializers.py)

- Standard ModelSerializer with all fields
- Extra read-only fields: `match_type_display`, `match_mode_display`, `created_by_email`
- `validate_match_value` — ensures non-empty
- `create` — auto-sets `created_by` from request user

### ViewSet: `CategoryRuleViewSet` (apps/transactions/views.py)

Standard ModelViewSet with extra actions:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/category-rules/` | GET | List all rules (filterable by match_type, match_mode, is_active; searchable by name, description, match_value) |
| `/api/v1/category-rules/` | POST | Create new rule |
| `/api/v1/category-rules/{id}/` | PATCH | Update rule |
| `/api/v1/category-rules/{id}/` | DELETE | Delete rule |
| `/api/v1/category-rules/{id}/test/` | POST | Test rule against transactions (max 1000), returns match count + 5 samples |
| `/api/v1/category-rules/apply_to_uncategorized/` | POST | Apply all active rules to uncategorized transactions |
| `/api/v1/category-rules/export-excel/` | GET | Export rules as .xlsx |

### Apply to Uncategorized Logic

The `apply_to_uncategorized` endpoint:
1. Finds all transactions where `prijem_vydaj=""` OR `druh=""`
2. For each, snapshots all 13 categorization fields (prijem_vydaj, vlastni_nevlastni, dane, druh, detail, kmen, 4x pct, projekt_id, produkt_id, podskupina_id)
3. Runs `apply_autodetection_rules()` on the transaction
4. Compares snapshot to current state — saves only if something changed
5. Returns `{ success, processed_count, updated_count }`

---

## Frontend (categories.html)

### Page Structure
- Rules table with columns: Název, Typ shody, Režim shody, Hodnota shody, P/V, Kategorie, Priorita, Aktivní, Akce
- Action buttons: Export Excel, Použít pravidla na nezařazené, + Přidat pravidlo
- Modal form for create/edit with all rule fields
- Info table showing match type hierarchy
- Lookup dropdowns (projekt, produkt, podskupina) loaded from API at page init

### CRUD Flow
- **Create:** Opens modal, fills form, POST to `/api/v1/category-rules/`
- **Edit:** Fetches rule data, populates modal, PATCH to `/api/v1/category-rules/{id}/`
- **Delete:** Confirm dialog, DELETE to `/api/v1/category-rules/{id}/`
- **Apply:** Confirm dialog, POST to `/api/v1/category-rules/apply_to_uncategorized/`, shows updated count

### API Integration (app.js)
- `api.getCategoryRules()` — GET list
- `api.createCategoryRule(data)` — POST create
- `api.updateCategoryRule(id, data)` — PATCH update
- `api.deleteCategoryRule(id)` — DELETE
- `api.applyRulesToUncategorized()` — POST apply

### Form Data Handling
All optional set_ fields are always sent in PATCH requests (so clearing a value actually clears it):
- String fields (`set_prijem_vydaj`, `set_vlastni_nevlastni`, `set_druh`, `set_detail`, `set_kmen`): sent as `''` when empty
- FK fields (`set_projekt`, `set_produkt`, `set_podskupina`): sent as `null` when empty
- Boolean `set_dane`: sent as `true` when checked, `null` when unchecked (null = don't set dane)

---

## Rules Applied During CSV Import

During `TransactionImporter._process_row()`:
1. Transaction object is created from CSV row data
2. `apply_autodetection_rules(transaction)` is called
3. If no rule set P/V, auto-determine from amount sign (positive=P, negative=V)
4. Transaction is saved

This means rules run on every newly imported transaction automatically.

---

## Known Issues & Gotchas

1. **First match wins globally** — only one rule ever applies per transaction, not one per match type. If a protiucet rule matches, no other rules are checked.

2. **"Uncategorized" definition** — `apply_to_uncategorized` only processes transactions where `prijem_vydaj` or `druh` is empty. Transactions with those fields set but missing other fields (e.g. projekt) are not re-processed.

3. **No bulk re-apply** — There's no way to re-apply rules to already-categorized transactions. Only uncategorized (empty P/V or druh) are processed.

4. **Rule cache lifetime** — The rules cache is per-importer-instance. For `apply_to_uncategorized`, a fresh cache is loaded each call. During CSV import, the cache lasts for the entire import batch.

5. **KMEN split validation** — Rules can set individual pct fields without enforcing the sum=100% constraint. The constraint is only validated on Transaction.clean(), so invalid splits from rules will fail on save.
