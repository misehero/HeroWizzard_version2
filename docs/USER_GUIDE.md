# Mise HERo Finance - User Guide

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Transactions](#3-transactions)
4. [Import CSV](#4-import-csv)
5. [Category Rules](#5-category-rules)
6. [Status Workflow](#6-status-workflow)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Getting Started

### Login

Open the application in your browser. You will see the login page.

- Enter your **email** and **password**
- Click **Login**
- On success, you are redirected to the Dashboard

Your session is maintained via JWT tokens stored in the browser. The session lasts 60 minutes before requiring a refresh (handled automatically), with a maximum of 7 days before re-login is needed.

### Navigation

The top navigation bar provides links to:

- **Dashboard** - Transaction overview with statistics and filters
- **Import CSV** - Upload bank statements
- **Categories** - Manage auto-categorization rules
- **Logout** - Sign out (top right, showing your email)

---

## 2. Dashboard

### Statistics Overview

Three summary cards at the top display:

| Card | Description |
|------|-------------|
| **Celkem transakcí** | Count of all transactions with status breakdown |
| **Příjmy / Výdaje** | Sum of income and expenses, plus net profit |
| **Zbývá vyřešit** | Role-dependent: transactions to process (accountant) or approve (manager/admin) |

Statistics update automatically when you apply filters or make changes.

### Transaction Table

Columns displayed:

| Column | Description |
|--------|-------------|
| Datum | Transaction date (DD.MM.YYYY) |
| Zdroj | Source icon (bank account, cash, card) |
| Popis | Message/note (truncated to 40 characters) |
| Protistrana | Counterparty name or merchant name |
| Částka | Color-coded: green for income, red for expenses |
| P/V | Income (P) or Expense (V) badge |
| Kategorie | Druh field value |
| Aktivní | Active/inactive toggle checkbox |
| Poslední změna | Who last modified and when |
| Actions | Edit button (pencil icon), audit log (admin only) |

**Note:** Status and Typ columns have been removed from the table to reduce clutter. Status is still available as a filter.

### Filters

| Filter | Description |
|--------|-------------|
| **Status** | Filter by transaction status (including "Čeká na schválení") |
| **P/V** | Filter by Income (P) or Expense (V) |
| **Od data / Do data** | Date range |
| **Zdroj** | Source: Účet, Hotovost, Karta |
| **Měna** | Currency: CZK, EUR |
| **KMEN** | Tribe filter |
| **Projekt** | Project dropdown |
| **Produkt** | Product dropdown |
| **Druh** | Cost type dropdown (populated from CostDetail lookup, grouped by Výdaje/Příjmy) |
| **Detail** | Cost detail dropdown (filtered by selected Druh) |
| **Hledat** | Free text search across description, counterparty, merchant, variable symbol |
| **Zobrazit neaktivní** | Include inactive transactions |

All filters apply immediately with a 300ms debounce. Pagination resets to page 1 when filters change.

### Pagination

- 50 transactions per page
- Previous/Next navigation buttons
- Page info shows: current page, total pages, total transaction count

---

## 3. Transactions

### Editing a Transaction

1. Click the **pencil icon** on any transaction row
2. A modal opens with the transaction details
3. **Imported transactions**: Bank fields (Date, Amount, Note, VS, Counterparty, Type, Currency) are **read-only** (greyed out)
4. **Manual transactions**: Bank fields are **editable** — you can modify Date, Amount, Note, VS, Counterparty, Type, and Currency
5. **Editable fields** (all transactions):
   - **Status** - Only visible to admin/manager (see Status Workflow below)
   - **P/V** - Příjem (Income) / Výdaj (Expense)
   - **V/N** - Výnosy / Náklady
   - **Druh** - Cost type
   - **Detail** - Cost detail
   - **Zodpovědná osoba** - Responsible person
   - **KMEN** - Tribe selector (MH, ŠK, XP, FR)
   - **KMEN %** - Four percentage fields (MH%, ŠK%, XP%, FR%) - must sum to exactly 100% or all be 0%
   - **Projekt** - Project dropdown
   - **Produkt** - Product dropdown
   - **Podskupina** - Subgroup dropdown (filtered by selected Product)
6. Click **Save** to persist changes
7. If not the last transaction, clicking Save opens the next transaction automatically

### Creating a Transaction Manually

1. Click the **+ Přidat transakci** button above the table
2. A modal opens with all fields editable (including bank fields)
3. **Required fields**: Date, Amount
4. **Auto-set fields**:
   - Status is set to "Upraveno" for admin/manager, or "Čeká na schválení" for accountant/viewer
   - Currency defaults to "CZK"
   - P/V is auto-determined from amount sign if not explicitly set (positive = P, negative = V)
5. Fill in desired fields and click **Save**

### KMEN Split Rules

The four percentage fields (MH%, ŠK%, XP%, FR%) represent the cost split across the four tribes. They must satisfy one of these conditions:

- **All zero** (0 + 0 + 0 + 0 = 0) - no split assigned
- **Sum to exactly 100%** (e.g., 100 + 0 + 0 + 0, or 25 + 25 + 25 + 25)

Any other sum will be rejected with a validation error.

---

## 4. Import CSV

### Supported Bank Formats

The system supports two bank import formats. Bank format is **auto-detected** from CSV headers — you do not need to specify which format you are uploading.

#### Creditas Bank

- **File format**: Semicolon-delimited CSV, Czech encoding (cp1250 or UTF-8)
- **Structure**: 3-row metadata header block (account info), then transaction header row, then data rows
- **Key headers**: Typ uctu, IBAN, BIC (metadata); Castka, Protiucet, Platba/Vklad (transactions)
- **Date format**: DD.MM.YYYY
- **Amount format**: Czech style with comma decimal and space thousands separator (e.g., "15 000,00")
- **Note**: Creditas CSVs do not contain a unique transaction ID, so re-importing the same file will create duplicate transactions

#### Raiffeisen Bank

- **File format**: Semicolon-delimited CSV, Czech encoding
- **Structure**: Single header row followed by data rows
- **Key headers**: Datum provedeni, Zauctovana castka, Nazev obchodnika
- **Date format**: DD.MM.YYYY HH:MM (datetime, time is stripped on import)
- **Amount format**: Czech style (e.g., "22 500,00")
- **Duplicate detection**: Uses the `Id transakce` field - re-importing the same file will skip already-imported transactions

### Upload Process

1. Navigate to the **Import CSV** page
2. Choose the appropriate card (Creditas or Raiffeisen)
3. Either **click** the upload zone to browse for a file, or **drag and drop** a file onto it
4. The filename appears once selected
5. Click **Nahrát a importovat**
6. Wait for processing to complete

### Import Results

After upload, a results summary is displayed:

| Field | Description |
|-------|-------------|
| **Celkem** | Number of data rows found in the CSV |
| **Importováno** | Successfully created transactions (green) |
| **Přeskočeno** | Duplicate transactions (already in system) |
| **Chyby** | Rows that failed to parse or validate (red) |

If there are errors, a detail table shows the row number and error message for each failed row.

### What Happens During Import

1. File is uploaded and encoding is auto-detected (UTF-8 with BOM, then cp1250 fallback)
2. Bank format is detected from CSV headers
3. Each row is parsed with Czech number and date format handling
4. For each transaction:
   - Duplicate check (by `id_transakce` if present)
   - Data type conversion (dates, decimals)
   - **Category rules are applied automatically** (see Section 5)
   - P/V is auto-set from amount sign (if not set by a rule)
   - Transaction is saved
5. An ImportBatch record tracks the operation for audit

### Import History

Below the upload cards, a history table shows all past imports with:
- Date, Filename, Status, Total rows, Imported, Skipped, Errors

---

## 5. Category Rules

Category rules allow automatic categorization of transactions during import and on-demand application.

### How Rules Work

Each rule defines:
1. **What to match** - A pattern to find in transaction data
2. **What to set** - Categorization fields to apply when matched

### Match Types (Priority Hierarchy)

Rules are evaluated in this order. The first match wins — if a higher-priority type matches, lower types are skipped:

| Priority | Match Type | Searches In | Example |
|----------|-----------|-------------|---------|
| 1 (Highest) | **Protiúčet** (Account Number) | Counterparty account number | `123456789/0100` |
| 2 | **Obchodník** (Merchant Name) | Merchant name field | `ALBERT`, `LIDL` |
| 3 | **VS** (Variable Symbol) | Variable symbol | `1234567890` |
| 4 | **Typ** (Transaction Type) | Transaction type from bank | `Příchozí platba` |
| 5 | **Město** (City) | Merchant city | `Praha`, `Brno` |
| 6 (Lowest) | **Klíčové slovo** (Keyword) | Message + notes + counterparty name (combined) | `FAKTURA`, `NAJEM` |

### Match Modes

| Mode | Behavior | Example |
|------|----------|---------|
| **Exact** (Přesná shoda) | Value must match exactly (case-insensitive by default) | `123456789/0100` matches only that exact account |
| **Contains** (Obsahuje) | Value must appear as substring | `ALBERT` matches "ALBERT HYPERMARKET" |
| **Starts With** (Začíná na) | Field must start with the value | `FAKTURA` matches "FAKTURA 12345" |

### Fields a Rule Can Set

When a rule matches, it can automatically set any of these transaction fields:

- P/V (Income/Expense)
- V/N (Výnosy/Náklady)
- Druh (Cost type) — selected from CostDetail lookup dropdown
- Detail (Cost detail) — filtered by selected Druh
- KMEN (Tribe: MH, ŠK, XP, FR)
- KMEN percentages (MH%, ŠK%, XP%, FR%)
- Projekt, Produkt, Podskupina

Only fields explicitly configured on the rule are set. Null/empty rule fields are skipped.

### Creating a Rule

1. Navigate to the **Pravidla kategorií** page
2. Click **+ Přidat pravidlo**
3. Fill in the form:
   - **Název pravidla** (required) - Descriptive name for the rule
   - **Typ shody** (required) - Protiúčet, Obchodník, VS, Typ, Město, or Klíčové slovo
   - **Režim shody** (required) - Přesná shoda, Obsahuje, or Začíná na
   - **Hodnota shody** (required) - The pattern to match against
   - **Priorita** - Lower number = higher priority within same match type (default: 100)
   - **Rozlišovat velká/malá** - Whether matching is case-sensitive (default: no)
   - **Nastavit P/V** - Income or Expense
   - **Nastavit V/N** - Výnosy or Náklady
   - **Nastavit kategorii (Druh)** - Dropdown from CostDetail lookup
   - **Nastavit detail** - Dropdown filtered by selected Druh
   - **Nastavit KMEN** - Tribe + percentage fields (MH%, ŠK%, XP%, FR%)
   - **Nastavit Projekt/Produkt/Podskupina** - Lookups
4. Click **Uložit pravidlo**

### Editing and Deleting Rules

- Click **Upravit** on any rule row to modify it
- Click **Smazat** to remove a rule (with confirmation)

### When Rules Are Applied

1. **During CSV import** - Every new transaction is automatically checked against all active rules before saving. This happens in the match type priority order. The first matching rule at any level wins.

2. **On demand** - Click the **Použít pravidla na nezařazené** button on the Categories page. This processes all transactions that have empty P/V or empty Druh and applies matching rules. A summary shows how many transactions were updated.

### Rule Priority Within Same Type

If multiple rules of the same match type could match a transaction, the rule with the **lowest priority number** is evaluated first. The first match wins.

---

## 6. Status Workflow

### Available Statuses

| Status | Badge | Description |
|--------|-------|-------------|
| **Importováno** | Blue | Initial status after CSV import |
| **Zpracováno** | Yellow | Processed by accountant |
| **Schváleno** | Green | Approved by manager/admin |
| **Upraveno** | Gray | Manually created or edited by admin/manager |
| **Čeká na schválení** | Orange | Auto-assigned when accountant/viewer saves any transaction |
| **Chyba** | Red | Error state |

### Role-Based Behavior

| Role | Can edit Status? | Auto-assign on save |
|------|-----------------|---------------------|
| **Admin** | Yes — any status | No auto-assign |
| **Manager** | Yes — any status | No auto-assign |
| **Accountant** | No | Status forced to "Čeká na schválení" |
| **Viewer** | No | Status forced to "Čeká na schválení" |

- When an **accountant** or **viewer** saves any transaction (edit or create), the status is automatically set to "Čeká na schválení"
- When a **manager** or **admin** edits a transaction, they see a Status dropdown and can set any status
- The Status column is no longer shown in the table but remains available as a filter

---

## 7. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Import failed" | CSV format doesn't match expected bank format | Ensure the file is an unmodified bank export |
| "No transactions imported, all skipped" | File was already imported (Raiffeisen) | Transactions with the same ID are skipped to prevent duplicates |
| Duplicate transactions after re-import | Creditas CSV has no transaction ID | Creditas files always create new transactions; avoid re-importing |
| "KMEN % must sum to 100" | Percentage fields don't total 100 | Adjust MH/ŠK/XP/FR percentages to sum to exactly 100, or set all to 0 |
| "Podskupina does not belong to product" | Subgroup-product mismatch | Select the correct product first, then choose a matching subgroup |
| Bank fields cannot be edited (imported) | By design | Bank-imported fields are read-only; only categorization fields can be edited |
| Bank fields cannot be edited (manual) | Bug | Manual transactions should have editable bank fields; report if still locked |
| Category rule not applying | Rule may be inactive or match value wrong | Check that the rule is active and test the match value against actual transaction data |
| "Pouze admin nebo manažer může měnit status" | Status editing restricted | Only admin/manager can explicitly set transaction status |
| Session expired | JWT token expired after 60 minutes | The app auto-refreshes tokens; if it fails, log in again |
