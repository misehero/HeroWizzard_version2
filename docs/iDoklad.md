# iDoklad Invoice Import

## Overview

Module 1 of iDoklad integration: CSV import and storage of invoices exported from iDoklad. Invoices are stored in a dedicated `IDokladInvoice` table, separate from bank transactions.

## IDokladInvoice Model

DB table: `transactions_idoklad_invoice`

22 fields organized into groups:

| Group | Fields |
|-------|--------|
| Identity | `cislo_dokladu` (unique, PK for dedup), `popis`, `cislo_objednavky`, `rada` |
| Customer | `nazev_jmeno`, `ic`, `dic_ic_dph`, `dic_sk` |
| Dates | `vystaveno`, `splatnost`, `duzp`, `datum_platby` |
| Amounts | `celkem_s_dph`, `celkem_bez_dph`, `dph`, `mena` |
| Payment | `stav_uhrady`, `uhrazena_castka` |
| Link key | `variabilni_symbol` (indexed, for future transaction matching) |
| Export flags | `exportovano`, `odeslano_odberateli`, `odeslano_uctovnemu` |
| Audit | `import_batch_id`, `created_at`, `created_by` |

Ordering: `-vystaveno` (newest first).

Indexes on `cislo_dokladu`, `variabilni_symbol`, `vystaveno`.

## IDokladImporter Service

Location: `apps/transactions/services.py`

### CSV Format

- Delimiter: comma (`,`)
- Encoding: UTF-8 with BOM (`utf-8-sig`)
- Dates: `MM/DD/YYYY` (US locale used by iDoklad export), also accepts `DD.MM.YYYY` and `YYYY-MM-DD`
- Amounts: period decimal separator, no thousand separator
- Booleans: `Ano` / `Ne`

### Column Mapping (`IDOKLAD_CSV_MAPPING`)

Maps 22 Czech CSV headers to model fields, e.g.:

```
"Cislo dokladu"    -> cislo_dokladu
"Celkem s DPH"     -> celkem_s_dph
"Variabilni symbol" -> variabilni_symbol
```

### Deduplication

By `cislo_dokladu` (unique constraint on model). If an invoice with the same `cislo_dokladu` already exists, the row is skipped (counted in `skipped`).

### Processing Flow

1. Parse CSV with `csv.DictReader` (comma delimiter)
2. For each row:
   - Extract `cislo_dokladu`; skip if already in DB
   - Convert types: dates via `_parse_date()`, decimals via `Decimal()`, booleans via `Ano/Ne` check
   - Create `IDokladInvoice` record
3. Track results in `ImportBatch` (same model used by bank CSV imports)
4. Return `ImportSummary` with counts

## Upload Endpoint

```
POST /api/v1/imports/upload-idoklad/
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <csv_file>
```

**Permission:** `IsAuthenticated`

**Response (201):**

```json
{
  "success": true,
  "batch_id": "uuid",
  "total_rows": 45,
  "imported": 40,
  "skipped": 5,
  "errors": 0,
  "duration_seconds": 0.3,
  "error_details": []
}
```

Uses the same `CSVUploadSerializer` and `ImportBatch` tracking as bank CSV uploads. Import history is visible alongside bank imports in the import batches list.

## What Works (Module 1)

- CSV upload and parsing of iDoklad export files
- Type conversion (dates, decimals, booleans)
- Deduplication by `cislo_dokladu`
- Storage in dedicated `IDokladInvoice` table
- Import batch tracking and error reporting

## What's NOT Implemented

- **Transaction enrichment via VS matching** -- invoices are stored but not linked to bank transactions
- No UI page for viewing stored invoices
- No export/listing endpoint for `IDokladInvoice` records

## Plan: Module 2

Match invoices to bank transactions by `variabilni_symbol`:

- `IDokladInvoice.variabilni_symbol` <-> `Transaction.variabilni_symbol`
- Copy relevant invoice fields (popis, IC, customer name, etc.) into transaction records or expose them via a joined API response
- Enable enriched views where bank transactions show associated invoice data
