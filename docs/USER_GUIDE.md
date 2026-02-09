# Mise HERo Finance - User Guide

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Transactions](#3-transactions)
4. [Import CSV](#4-import-csv)
5. [Category Rules](#5-category-rules)
6. [Troubleshooting](#6-troubleshooting)

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

Four summary cards at the top display:

| Card | Description |
|------|-------------|
| **Total Transactions** | Count of all transactions |
| **Total Income** | Sum of positive amounts (green) |
| **Total Expenses** | Sum of negative amounts (red) |
| **Uncategorized** | Count of transactions missing P/V or Druh |

Statistics update automatically when you apply filters or make changes.

### Transaction Table

Columns displayed:

| Column | Description |
|--------|-------------|
| Date | Transaction date (DD.MM.YYYY) |
| Type | Transaction type |
| Description | Message/note (truncated to 40 characters) |
| Counterparty | Counterparty name or merchant name |
| Amount | Color-coded: green for income, red for expenses |
| Status | Badge: Importovano, Zpracovano, Schvaleno, Upraveno, Chyba |
| P/V | Income (P) or Expense (V) badge |
| Category | Druh field value |
| Actions | Edit button (pencil icon) |

### Filters

- **Status** - Filter by transaction status
- **Type** - Filter by Income (P) or Expense (V)
- **Date range** - From/To date inputs
- **Search** - Free text search across description, counterparty, merchant, variable symbol

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
3. **Bank fields are read-only** (greyed out): Date, Amount, Note, VS, Counterparty, Type
4. **Editable fields**:
   - **Status** - Importovano, Zpracovano, Schvaleno, Upraveno, Chyba
   - **P/V** - Prijem (Income) / Vydaj (Expense)
   - **V/N** - Vlastni (Own) / Nevlastni (Not own)
   - **Dane** - Tax-related checkbox
   - **Druh** - Cost type (free text)
   - **Detail** - Cost detail (free text)
   - **KMEN** - Tribe selector (MH, SK, XP, FR)
   - **KMEN %** - Four percentage fields (MH%, SK%, XP%, FR%) - must sum to exactly 100% or all be 0%
   - **Projekt** - Project dropdown
   - **Produkt** - Product dropdown
   - **Podskupina** - Subgroup dropdown (filtered by selected Product)
5. Click **Save** to persist changes

### Creating a Transaction Manually

1. Click the **+ Add Transaction** button above the table
2. A modal opens with all fields editable (including bank fields)
3. **Required fields**: Date, Amount
4. **Auto-set fields**:
   - Status is set to "Upraveno" automatically
   - Currency is set to "CZK"
   - P/V is auto-determined from amount sign if not explicitly set (positive = P, negative = V)
5. Fill in desired fields and click **Save**

### KMEN Split Rules

The four percentage fields (MH%, SK%, XP%, FR%) represent the cost split across the four tribes. They must satisfy one of these conditions:

- **All zero** (0 + 0 + 0 + 0 = 0) - no split assigned
- **Sum to exactly 100%** (e.g., 100 + 0 + 0 + 0, or 25 + 25 + 25 + 25)

Any other sum will be rejected with a validation error.

---

## 4. Import CSV

### Supported Bank Formats

The system supports three import formats. Bank format is **auto-detected** from CSV headers - you do not need to specify which format you are uploading.

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

#### iDoklad (Invoices)

- **File format**: Comma-delimited CSV, UTF-8
- **Purpose**: Invoice data (stored separately from bank transactions)
- **Date format**: MM/DD/YYYY
- **Note**: Invoices can later be matched to transactions via variable symbol

### Upload Process

1. Navigate to the **Import CSV** page
2. Choose the appropriate card (Creditas, Raiffeisen, or iDoklad)
3. Either **click** the upload zone to browse for a file, or **drag and drop** a file onto it
4. The filename appears once selected
5. Click **Upload & Import**
6. Wait for processing to complete

### Import Results

After upload, a results summary is displayed:

| Field | Description |
|-------|-------------|
| **Total** | Number of data rows found in the CSV |
| **Imported** | Successfully created transactions (green) |
| **Skipped** | Duplicate transactions (already in system) |
| **Errors** | Rows that failed to parse or validate (red) |

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

Rules are evaluated in this order. The first match wins at each level:

| Priority | Match Type | Searches In | Example |
|----------|-----------|-------------|---------|
| 1 (Highest) | **Protiucet** (Account Number) | Counterparty account number | `123456789/0100` |
| 2 | **Merchant** (Merchant Name) | Merchant name field | `ALBERT`, `LIDL` |
| 3 (Lowest) | **Keyword** | Message + notes + counterparty name (combined) | `FAKTURA`, `NAJEM` |

### Match Modes

| Mode | Behavior | Example |
|------|----------|---------|
| **Exact** | Value must match exactly (case-insensitive by default) | `123456789/0100` matches only that exact account |
| **Contains** | Value must appear as substring | `ALBERT` matches "ALBERT HYPERMARKET" |
| **Regex** | Regular expression pattern matching | `FAKTURA\s*\d+` matches "FAKTURA 12345" |

### Fields a Rule Can Set

When a rule matches, it can automatically set any of these transaction fields:

- P/V (Income/Expense)
- V/N (Own/Not own)
- Dane (Tax flag)
- Druh (Cost type)
- Detail (Cost detail)
- KMEN (Tribe: MH, SK, XP, FR)
- KMEN percentages (MH%, SK%, XP%, FR%)
- Projekt, Produkt, Podskupina

Only fields explicitly configured on the rule are set. Null/empty rule fields are skipped.

### Creating a Rule

1. Navigate to the **Categories** page
2. Click **+ Add Rule**
3. Fill in the form:
   - **Name** (required) - Descriptive name for the rule
   - **Match Type** (required) - Protiucet, Merchant, or Keyword
   - **Match Mode** (required) - Exact, Contains, or Regex
   - **Match Value** (required) - The pattern to match against
   - **Priority** - Lower number = higher priority within same match type (default: 100)
   - **Case Sensitive** - Whether matching is case-sensitive (default: no)
   - Configure which fields to set when matched (all optional)
4. Click **Save**

### Editing and Deleting Rules

- Click **Edit** on any rule row to modify it
- Click **Delete** to remove a rule (with confirmation)

### When Rules Are Applied

1. **During CSV import** - Every new transaction is automatically checked against all active rules before saving. This happens in the match type priority order (Account > Merchant > Keyword). The first matching rule at any level wins.

2. **On demand** - Click the **Apply Rules to Uncategorized** button on the Categories page. This processes all transactions that have empty P/V or empty Druh and applies matching rules. A summary shows how many transactions were updated.

### Rule Priority Within Same Type

If multiple rules of the same match type could match a transaction, the rule with the **lowest priority number** is evaluated first. The first match wins.

---

## 6. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Import failed" | CSV format doesn't match expected bank format | Ensure the file is an unmodified bank export |
| "No transactions imported, all skipped" | File was already imported (Raiffeisen) | Transactions with the same ID are skipped to prevent duplicates |
| Duplicate transactions after re-import | Creditas CSV has no transaction ID | Creditas files always create new transactions; avoid re-importing |
| "KMEN % must sum to 100" | Percentage fields don't total 100 | Adjust MH/SK/XP/FR percentages to sum to exactly 100, or set all to 0 |
| "Podskupina does not belong to product" | Subgroup-product mismatch | Select the correct product first, then choose a matching subgroup |
| Bank fields cannot be edited | By design | Bank-imported fields (date, amount, etc.) are read-only; only categorization fields can be edited |
| Category rule not applying | Rule may be inactive or match value is wrong | Check that the rule is active and test the match value against actual transaction data |
| Session expired | JWT token expired after 60 minutes | The app auto-refreshes tokens; if it fails, log in again |
