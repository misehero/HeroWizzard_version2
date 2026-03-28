# Upgrade Guide — HeroWizzard

## Version History

| Version | Date | Branch | Key Changes |
|---------|------|--------|-------------|
| v3 | 09.02.2026 | all | Backup/restore (transactions only), soft-delete |
| v4 | 13.02.2026 | all | Czech translation, audit log, P/V validation |
| v5 | 08.03.2026 | all | Full backup (transactions + rules + batches + audit), API_BASE auto-detect, Číselníky management (Projekt/Produkt/Podskupina), sort_order, lookups in backup, daily auto-backups, server backup restore UI |
| v6 | 10.03.2026 | all | Category rules (6 match types, 3 modes), user management page, forgot password, Excel export, CSV import (3 bank formats + auto-detection) |
| v7 | 16.03.2026 | all | Sortable columns, favicon, responsive dashboard, environment detection for new domains |
| v8 | 21.03.2026 | all | Druh/detail filters, status workflow (Čeká na schválení), manual transaction field editing, category rules improvements (druh dropdown, KMEN pct), Účet/Protiúčet fields, per-env deploy keys, deploy lock + auto-rollback |
| v9 | 23.03.2026 | all | CostDetail with 105 real Druh/Detail combinations from Excel, cascading dropdowns in transaction modal (P/V → Druh → Detail → Poznámka hint), Číselníky CRUD for CostDetail, backup v6 (includes cost_details), /status and /release skills |
| v10 | 24.03.2026 | all | Číselníky refactoring (no pagination for lookups, textarea fields, editable Typ dropdown, in-place deactivate/reactivate with counts), module switcher dropdown (admin-only, 3 modules: Finance/Fakturace/Reporty), dynamic navbar from centralized config |

## Standard Upgrade Process

### 1. Before upgrading — backup current data

```bash
# Option A: App-level backup (via browser)
# Login as admin → Dashboard → "Export zálohy" button → saves JSON file

# Option B: Database-level backup (via SSH)
ssh deploy@46.101.121.250
sudo -u postgres pg_dump misehero_<env> > /tmp/misehero_<env>_backup_$(date +%Y%m%d).sql
```

### 2. Make changes on feature branch

```bash
git checkout stage  # or develop
git checkout -b feat/your-feature
# ... make changes ...
git add <files>
git commit -m "feat: description"
git push -u origin feat/your-feature
```

### 3. Merge to target branch

```bash
git checkout stage
git merge feat/your-feature
git push origin stage
```

### 4. Deploy

```bash
ssh deploy@46.101.121.250
cd /var/www/misehero-stage  # or test/production
bash deploy/deploy.sh stage  # or test/production
```

The deploy script automatically:
1. Pulls latest code from the branch
2. Installs Python dependencies
3. Runs database migrations
4. Collects static files
5. Restarts the gunicorn service
6. Runs a health check

### 5. Verify

- Check the login page shows correct version
- Test key functionality
- Check error logs: `tail -f /var/www/misehero-<env>/logs/gunicorn-error.log`

## Promoting Between Environments

Flow: `develop` → `stage` → `production`

```bash
# Promote stage to production
git checkout production
git merge stage
git push origin production

# Deploy production
ssh deploy@46.101.121.250
cd /var/www/misehero-production
bash deploy/deploy.sh production
```

## Updating the Version String

Edit `frontend/version.json`:

```json
{
  "version": "v8",
  "date": "21.03.2026"
}
```
Format: version is `v<major>`, date is `DD.MM.YYYY` (Czech format). The frontend (`app.js`) loads this file dynamically.

## Data Migration Between Environments

### Using app-level backup (v6 format)

1. On source environment: Login as admin → "Export zálohy" → download JSON
2. On target environment: Login as admin → "Import zálohy" → upload JSON
3. Confirm the warning (all existing data will be replaced)

The v6 backup includes: transactions, category rules, import batches, audit logs, all lookups (projects, products, subgroups, cost_details).
Users and roles are NOT affected.

### Using database dump

```bash
# On server:
# 1. Backup source
sudo -u postgres pg_dump misehero_test > /tmp/backup.sql

# 2. Stop target service
sudo systemctl stop misehero-stage

# 3. Drop and recreate target DB
sudo -u postgres psql -c 'DROP DATABASE misehero_stage;'
sudo -u postgres psql -c 'CREATE DATABASE misehero_stage OWNER misehero_stage_user;'

# 4. Restore
sudo -u postgres psql misehero_stage < /tmp/backup.sql

# 5. Fix permissions
sudo -u postgres psql -c 'GRANT ALL ON ALL TABLES IN SCHEMA public TO misehero_stage_user;' misehero_stage
sudo -u postgres psql -c 'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO misehero_stage_user;' misehero_stage

# 6. Start target service
sudo systemctl start misehero-stage
```

## Rollback

If a deploy fails:
```bash
# Check what went wrong
sudo journalctl -u misehero-<env> --no-pager -n 50

# Revert to previous commit
cd /var/www/misehero-<env>
git log --oneline -5  # find the good commit
git checkout <good-commit-hash>
sudo systemctl restart misehero-<env>
```

For data rollback, restore from the backup taken in step 1.

## IMPORTANT: Backup/Restore and Schema Changes

When you add/modify database models (new fields, new tables), you MUST also update the backup/restore code in `apps/transactions/views.py`:

1. **export_backup()** — add new fields/models to the JSON output
2. **import_backup()** — add restore logic for new fields/models
3. **TRUNCATE statement** — add new table names if new models are added
4. **Bump backup version** — increment `"version"` in the JSON payload

The backup JSON currently includes (v6):
- `transactions` — all Transaction fields
- `category_rules` — all CategoryRule fields
- `import_batches` — ImportBatch records
- `audit_logs` — TransactionAuditLog records
- `projects` — Project lookup records
- `products` — Product lookup records
- `product_subgroups` — ProductSubgroup lookup records
- `cost_details` — CostDetail (Druh/Detail/Poznámka) lookup records

If you add new models (e.g., recurring transactions, budgets), they must be added to both export and import.

## Daily Automatic Backups

**Status:** Implemented (all 3 environments)

- Management command: `python manage.py backup_to_json`
- Systemd timers: `misehero-backup-test`, `misehero-backup-stage`, `misehero-backup-production`
- Schedule: midnight Prague time (Europe/Prague), daily
- Path: `/var/www/misehero-{env}/backups/backup_YYYY-MM-DD_HH-MM.json`
- Retention: 30 days (auto-cleanup of older files)
- Logs: `journalctl -u misehero-backup-{env}`

### Data integrity notes

- Use `TRUNCATE ... CASCADE` (not Django ORM `.delete()`) for bulk table wipes — PostgreSQL has RESTRICT FK constraints at DB level
- Always wrap restore in `db_transaction.atomic()` so any failure triggers full rollback
- When adding new models, update: export, import, TRUNCATE statement, and backup version number

## Known Issues

- **Browser caching**: After deploy, users may need `Ctrl+Shift+R` to see new frontend changes. Frontend files have no cache-busting mechanism yet.
- **No swap on server**: The 2GB droplet has no swap configured. Under heavy load, OOM killer may terminate workers.
