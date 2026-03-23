---
name: status
description: Check system health across all Mise HERo Finance environments — services, API, database, backups, versions, and SSL.
disable-model-invocation: true
argument-hint: "test|stage|production|all"
---

# System Health Check — Mise HERo Finance

Check the health and status of Mise HERo Finance environments.

**Target:** `$ARGUMENTS` (default: `all`)

## Environment Map

| Environment | API Base URL                                    | SSH Service         |
|-------------|------------------------------------------------|---------------------|
| test        | https://test.herowizzard.misehero.cz/api/v1   | misehero-test       |
| stage       | https://stage.herowizzard.misehero.cz/api/v1  | misehero-stage      |
| production  | https://herowizzard.misehero.cz/api/v1        | misehero-production |

**Server:** 46.101.121.250, SSH user: `deploy`

## Steps

### 1. Validate Arguments

- If `$ARGUMENTS` is empty, default to `all` (check all environments).
- Valid values: `test`, `stage`, `production`, `all`.

### 2. For Each Target Environment, Check:

#### a) API Health
```bash
# Check API responds (expect 405 for token endpoint = API is running)
curl -sk -o /dev/null -w "%{http_code}" {API_BASE_URL}/auth/token/
```
- 405 or 200 = healthy
- 502/503/000 = service down

#### b) Version
```bash
curl -sk {BASE_URL}/version.json
```
Parse and display the version number and date.

#### c) Service Status (via SSH)
```bash
ssh -i .deploy_key_{env} -o StrictHostKeyChecking=no deploy@46.101.121.250 "systemctl is-active misehero-{env}"
```

#### d) Database Connectivity
```bash
# Try to fetch a simple API endpoint
curl -sk -w "\n%{http_code}" "{API_BASE_URL}/projects/"
```
If it returns data, DB is connected.

#### e) Latest Backup
```bash
ssh -i .deploy_key_{env} -o StrictHostKeyChecking=no deploy@46.101.121.250 "ls -lt /var/www/misehero-{env}/backups/ | head -3"
```
Report the most recent backup file and its age.

#### f) SSL Certificate
```bash
echo | openssl s_client -connect {DOMAIN}:443 -servername {DOMAIN} 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null
```

#### g) Disk Space
```bash
ssh -i .deploy_key_{env} -o StrictHostKeyChecking=no deploy@46.101.121.250 "df -h / | tail -1"
```
Only run once (same server for all envs).

### 3. Report

Print a summary table per environment:

```
## System Status — {date}

### {Environment}
| Check          | Status | Details                    |
|----------------|--------|----------------------------|
| API            | ✅/❌   | HTTP {code}                |
| Version        | ✅     | v{X} ({date})              |
| Service        | ✅/❌   | active/inactive            |
| Database       | ✅/❌   | {record count} projects    |
| Latest Backup  | ✅/⚠️   | {filename} ({age})         |
| SSL Cert       | ✅/⚠️   | Expires {date}             |
| Disk Space     | ✅/⚠️   | {used}% used               |
```

### 4. Alerts

Flag any of these conditions:
- **CRITICAL:** Service inactive, API unreachable, database connection failed
- **WARNING:** Backup older than 48 hours, SSL expires within 30 days, disk > 80% used
- **INFO:** Version mismatch between environments (expected during staged rollouts)

## SSH Key Selection

Use the environment-specific deploy key:
- test: `.deploy_key_test`
- stage: `.deploy_key_stage`
- production: `.deploy_key_production`

If per-environment keys don't exist, fall back to `.deploy_key`.

## Safety Rules

- This is a **read-only** operation — never modify anything
- Never expose database credentials or sensitive config in output
- If SSH fails, still report what's available via HTTP checks
