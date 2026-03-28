# Deployment Manual — Mise HERo Finance

## Infrastructure Overview

**Server:** DigitalOcean droplet `46.101.121.250` (Ubuntu 24.04, 2GB RAM, 1 vCPU)

Three environments run on the same droplet:

| Environment | Branch     | Port | Service             | Database               | URL                                        |
|-------------|-----------|------|---------------------|------------------------|--------------------------------------------|
| test        | develop    | 8001 | misehero-test       | misehero_test          | https://test.herowizzard.misehero.cz/      |
| stage       | stage      | 8002 | misehero-stage      | misehero_stage         | https://stage.herowizzard.misehero.cz/     |
| production  | production | 8003 | misehero-production | misehero_production    | https://herowizzard.misehero.cz/           |

**Nginx** reverse-proxies all three on port 443 with SSL (wildcard cert for `*.herowizzard.misehero.cz`).

---

## SSH Access

### Per-Environment Deploy Keys

Each environment has its own SSH key for isolation:

| Environment | Key File                | Comment              |
|-------------|------------------------|----------------------|
| test        | `.deploy_key_test`      | deploy-test@misehero |
| stage       | `.deploy_key_stage`     | deploy-stage@misehero|
| production  | `.deploy_key_production`| deploy-production@misehero |

**Usage:**
```bash
ssh -i .deploy_key_test deploy@46.101.121.250 "echo 'connected to test'"
ssh -i .deploy_key_stage deploy@46.101.121.250 "echo 'connected to stage'"
ssh -i .deploy_key_production deploy@46.101.121.250 "echo 'connected to production'"
```

All keys connect as user `deploy`. The legacy shared `.deploy_key` is deprecated.

**Key locations:**
- Local: project root (gitignored)
- Server: `~deploy/.ssh/authorized_keys`
- GitHub Actions: stored as repository secrets (`DO_SSH_KEY_TEST`, `DO_SSH_KEY_STAGE`, `DO_SSH_KEY_PRODUCTION`)

### Key Rotation

To rotate a key:
1. Generate new key: `ssh-keygen -t ed25519 -C "deploy-{env}@misehero" -f .deploy_key_{env} -N ""`
2. Add new public key to server: `ssh -i .deploy_key_{env} deploy@46.101.121.250 "echo '{new_pub_key}' >> ~/.ssh/authorized_keys"`
3. Test new key works
4. Remove old key from `authorized_keys`
5. Update GitHub secret `DO_SSH_KEY_{ENV}` with new private key

---

## Deployment Methods

### Method 1: Claude Code `/deploy` Skill (Recommended)

```
/deploy test
/deploy stage
/deploy production
/deploy all
```

The skill handles: pre-flight checks, version update, confirmation gates, deployment, health checks, rollback, and history logging.

**Production requires two-step confirmation** — you must type `DEPLOY` to proceed.

### Method 2: Direct SSH

```bash
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && bash deploy/deploy.sh {env}"
```

### Method 3: GitHub Actions (CI/CD)

Push to the branch triggers automatic deployment:
- Push to `develop` → deploys to test
- Push to `stage` → deploys to stage
- Push to `production` → deploys to production (requires environment approval in GitHub)

Workflows: `.github/workflows/deploy-{env}.yml`

---

## Deploy Script (`deploy/deploy.sh` v2)

The deploy script runs on the server and handles:

1. **Lock acquisition** — prevents concurrent deploys to the same environment
2. **Pre-deploy snapshot** — saves current commit hash for rollback
3. **Git pull** from the correct branch
4. **pip install** dependencies
5. **Django migrations**
6. **collectstatic**
7. **Service restart**
8. **Health check** — verifies service is running and API responds
9. **Auto-rollback** — if health check fails, reverts to previous commit automatically
10. **Version verification** — prints deployed version.json

### Lock File

Location: `/tmp/misehero-deploy-{env}.lock`

Contains the PID of the deploy process. If a lock exists:
- If PID is alive → another deploy is in progress, wait
- If PID is dead → stale lock, auto-removed

### Rollback File

Location: `/tmp/misehero-rollback-{env}.txt`

Contains the commit hash before the deploy started. Used for automatic rollback.

---

## Manual Rollback

If you need to rollback manually:

```bash
# Check previous commit
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cat /tmp/misehero-rollback-{env}.txt"

# Rollback to specific commit
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && git reset --hard {commit} && sudo systemctl restart misehero-{env}"

# Verify
ssh -i .deploy_key_{env} deploy@46.101.121.250 "systemctl is-active misehero-{env} && cd /var/www/misehero-{env} && git log --oneline -1"
```

---

## Version Tracking

Version is stored in `frontend/version.json`:
```json
{
  "version": "v10",
  "date": "24.03.2026"
}
```

- Loaded dynamically by `app.js` on login page and app header
- Must be updated before every deployment
- Date format: `DD.MM.YYYY` (Czech)

---

## Branch Strategy

```
develop  ──→  stage  ──→  production
   │            │              │
   ▼            ▼              ▼
  TEST        STAGE        PRODUCTION
```

- **develop**: integration branch, deploys to TEST
- **stage**: pre-production, deploys to STAGE
- **production**: live, deploys to PRODUCTION
- **main**: reference/GitHub default branch, kept in sync

### Promoting Code

```bash
# Stage → Production
git checkout production
git merge stage
git push origin production

# Then deploy (via /deploy production or push triggers CI/CD)
```

---

## GitHub Actions Setup

### Repository Secrets

| Secret                 | Value              | Scope       |
|------------------------|-------------------|-------------|
| `DO_HOST`              | `46.101.121.250`  | Repository  |
| `DO_SSH_USER`          | `deploy`          | Repository  |
| `DO_SSH_KEY_TEST`      | Private key       | Environment: test |
| `DO_SSH_KEY_STAGE`     | Private key       | Environment: stage |
| `DO_SSH_KEY_PRODUCTION`| Private key       | Environment: production |

### Environments

Create three environments in GitHub → Settings → Environments:
- **test** — no restrictions
- **stage** — no restrictions
- **production** — enable "Required reviewers" for approval before deploy

### Setting Up Secrets

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add `DO_HOST` and `DO_SSH_USER` as repository secrets
3. Create environments (test, stage, production) under Settings → Environments
4. For each environment, add `DO_SSH_KEY_{ENV}` with the contents of `.deploy_key_{env}` (private key)
5. For production environment, add yourself as required reviewer

---

## Monitoring & Troubleshooting

### Service Status
```bash
ssh -i .deploy_key_{env} deploy@46.101.121.250 "systemctl status misehero-{env}"
```

### Logs
```bash
# Gunicorn service logs
ssh -i .deploy_key_{env} deploy@46.101.121.250 "sudo journalctl -u misehero-{env} --no-pager -n 50"

# Application error log
ssh -i .deploy_key_{env} deploy@46.101.121.250 "tail -50 /var/www/misehero-{env}/logs/gunicorn-error.log"
```

### Health Check
```bash
ssh -i .deploy_key_{env} deploy@46.101.121.250 "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:{port}/api/v1/"
```

### Database
```bash
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && set -a && source .env && set +a && /var/www/misehero-{env}/venv/bin/python manage.py showmigrations"
```

---

## Backups

### Automatic Daily Backups
- All 3 environments: midnight Prague time
- 30-day retention
- Path: `/var/www/misehero-{env}/backups/backup_YYYY-MM-DD_HH-MM.json`
- Systemd timers: `misehero-backup-test`, `misehero-backup-stage`, `misehero-backup-production`

### Manual Backup
```bash
# App-level (via browser)
Login as admin → Dashboard → "Export zálohy" → saves JSON

# Database-level
ssh -i .deploy_key_{env} deploy@46.101.121.250 "sudo -u postgres pg_dump misehero_{env} > /tmp/backup_$(date +%Y%m%d).sql"
```

---

## Security Checklist

- [ ] Each environment uses its own SSH key
- [ ] Production deployments require explicit confirmation
- [ ] GitHub Actions production environment has required reviewers
- [ ] `.deploy_key_*` files are in `.gitignore`
- [ ] Legacy shared `.deploy_key` removed from `authorized_keys` (after verification)
- [ ] SSH keys rotated at least annually
- [ ] `.env` files on server contain no passwords with `!` (shell escaping issue)
- [ ] SSL cert covers all domains (`*.herowizzard.misehero.cz`)

---

## DNS Notes

**Correct domains** (point to droplet `46.101.121.250`):
- `herowizzard.misehero.cz`
- `test.herowizzard.misehero.cz`
- `stage.herowizzard.misehero.cz`

**Wrong domains** (point to WordPress at `46.28.105.11` — do NOT use):
- `stage.misehero.cz`
- `app.misehero.cz`
