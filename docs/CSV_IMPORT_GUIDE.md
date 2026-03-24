# CSV Import Guide

## Supported Formats

Three bank CSV formats are supported with automatic detection from headers:

| Format | Detection Headers | Delimiter | Encoding | Dedup Field | Date Format |
|--------|------------------|-----------|----------|-------------|-------------|
| **Creditas** | `Typ účtu`, `IBAN`, `BIC` | `;` | cp1250 / utf-8-sig | None (no dedup) | DD.MM.YYYY |
| **Raiffeisen** | `Datum provedení`, `Zaúčtovaná částka` | `;` | cp1250 / utf-8-sig | `id_transakce` | DD.MM.YYYY HH:MM (time stripped) |
| **Generic** | Default fallback | `;` | utf-8-sig | `id_transakce` | DD.MM.YYYY |

Number format: Czech style — `1 234,56` (space thousands, comma decimal).

Column mappings are defined in `apps/transactions/services.py` as `CREDITAS_CSV_MAPPING`, `RAIFFEISEN_CSV_MAPPING`, and `GENERIC_CSV_MAPPING`.

## Format Detection Logic

In `TransactionImporter._detect_bank_format()`:

1. Read headers from first data row
2. If Creditas signature headers (`Typ účtu`, `IBAN`, `BIC`) are ALL present → **creditas**
3. If Raiffeisen signature headers (`Datum provedení`, `Zaúčtovaná částka`, `Název obchodníka`) have ANY match → **raiffeisen**
4. Otherwise → **generic** (fallback)

### Creditas Special Handling

- CSV has a 3-row metadata header block (account info) before the transaction header row
- The importer skips lines until it finds the actual column headers
- Account number is split across two columns (`Můj účet` + `Můj účet-banka`) and joined
- **No transaction ID field** — re-importing the same file creates duplicates. This is by design; Creditas exports don't include unique identifiers.

### Raiffeisen Special Handling

- Single header row, standard structure
- Datetime in `Datum provedení` — time portion is stripped, only date kept
- Has `Id transakce` field → duplicates are detected and skipped on re-import

## Import Processing Flow

`TransactionImporter.import_csv()`:

1. Read file, detect encoding (try utf-8-sig, fall back to cp1250)
2. Detect bank format from headers
3. Parse rows using format-specific mapping
4. For each row:
   - Convert types: dates via `_parse_date()`, decimals via `_parse_czech_decimal()`
   - Check for duplicate (by `id_transakce` if present)
   - Create `Transaction` object
   - **Apply category rules** automatically (see `docs/CATEGORY_RULES.md`)
   - Auto-set P/V from amount sign if no rule set it (positive=P, negative=V)
   - Save transaction
5. Track results in `ImportBatch` record (filename, counts, errors, timestamps)

## Import Methods

### REST API (primary — used by frontend)

```
POST /api/v1/imports/upload/
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <csv_file>
```

Returns: `{ success, batch_id, total_rows, imported, skipped, errors, duration_seconds, error_details }`

### Management Command (CLI)

```bash
python manage.py import_csv <file>              # basic import
python manage.py import_csv <file> --dry-run    # parse only, no save
python manage.py import_csv <file> --no-rules   # skip auto-categorization
python manage.py import_csv <file> --user admin@misehero.cz  # attribute to user
```

## ImportBatch Tracking

Each import creates an `ImportBatch` record for audit:
- Statuses: `pending` → `processing` → `completed` (or `failed` / `rolled_back`)
- Tracks: filename, row counts (total/imported/skipped/errors), timestamps, user
- Error details stored as JSON array with row number and error message per failed row

## Duplicate Detection

| Format | Behavior | Mechanism |
|--------|----------|-----------|
| Raiffeisen | Skips duplicates | `UniqueConstraint` on `id_transakce` (non-empty) |
| Creditas | Creates duplicates | No transaction ID in export — avoid re-importing same file |
| Generic | Skips duplicates | Same as Raiffeisen |

## iDoklad CSV Import

Separate importer for iDoklad invoice CSVs. See `docs/iDoklad.md` for details.

## Test Data

Sample files in `docs/test-data/`:

| File | Format | Rows |
|------|--------|------|
| `test_creditas.csv` | Creditas | 5 |
| `test_raiffeisen.csv` | Raiffeisen | 5 |
| `sample_raiffeisen.csv` | Raiffeisen | 10 |
