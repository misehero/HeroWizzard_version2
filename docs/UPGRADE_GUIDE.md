# Upgrade Guide — HeroWizzard

## Version History

| Version | Date | Branch | Key Changes |
|---------|------|--------|-------------|
| v3 | 09.02.2026 | all | Backup/restore (transactions only), soft-delete |
| v4 | 13.02.2026 | all | Czech translation, audit log, P/V validation |
| v5 | 08.03.2026 | stage | Full backup (transactions + rules + batches + audit), API_BASE auto-detect |

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

Edit `frontend_demo/app.js`, line with `versionInfo.textContent`:
```javascript
versionInfo.textContent = 'v5 | 8.03.2026';
```
Format: `v<major> | <D.MM.YYYY>`

## Data Migration Between Environments

### Using app-level backup (v5 format)

1. On source environment: Login as admin → "Export zálohy" → download JSON
2. On target environment: Login as admin → "Import zálohy" → upload JSON
3. Confirm the warning (all existing data will be replaced)

The v5 backup includes: transactions, category rules, import batches, audit logs.
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

## Known Issues

- **Browser caching**: After deploy, users may need `Ctrl+Shift+R` to see new frontend changes. Frontend files have no cache-busting mechanism yet.
- **No swap on server**: The 2GB droplet has no swap configured. Under heavy load, OOM killer may terminate workers.
