---
name: deploy
description: Deploy Mise HERo Finance to DigitalOcean droplet environments (test, stage, production). Use when the user wants to deploy, push to server, or update environments.
disable-model-invocation: true
argument-hint: [test|stage|production|all]
---

# Deploy Mise HERo Finance

Deploy to DigitalOcean droplet at `46.101.121.250` using SSH key `.deploy_key` as user `deploy`.

**Target:** `$ARGUMENTS`

## Environment Map

| Environment | Branch       | Server Path                    | Port | Service Name         | URL                              |
|-------------|-------------|--------------------------------|------|----------------------|----------------------------------|
| test        | develop      | /var/www/misehero-test         | 8001 | misehero-test        | https://test.herowizzard.misehero.cz/ |
| stage       | stage        | /var/www/misehero-stage        | 8002 | misehero-stage       | https://stage.herowizzard.misehero.cz/ |
| production  | production   | /var/www/misehero-production   | 8003 | misehero-production  | https://herowizzard.misehero.cz/ |

## Version Tracking

Version and date are stored in `frontend_demo/version.json`:
```json
{
  "version": "v8",
  "date": "21.03.2026"
}
```

This file is the **single source of truth** for the version displayed on the login page and in the app header on all pages. The frontend (`app.js`) loads this file dynamically.

## Deployment History

Deployment history is tracked in `.claude/deployment_history.md`. **You MUST update this file after every deployment.**

## Deployment Steps

Follow these steps **exactly** for each environment being deployed:

### 1. Validate Arguments

- If `$ARGUMENTS` is empty, ask which environment(s) to deploy: test, stage, production, or all.
- If `$ARGUMENTS` is `all`, deploy in order: **test → stage → production**, confirming after each.
- Valid values: `test`, `stage`, `production`, `all`.

### 2. Pre-flight Checks

Before deploying each environment, run these checks:

```bash
# Check SSH connectivity
ssh -i .deploy_key -o ConnectTimeout=5 deploy@46.101.121.250 "echo 'SSH OK'"
```

```bash
# Check current status of the target service
ssh -i .deploy_key deploy@46.101.121.250 "systemctl is-active misehero-{env} && echo 'Service running' || echo 'Service NOT running'"
```

```bash
# Check for uncommitted changes on the server
ssh -i .deploy_key deploy@46.101.121.250 "cd /var/www/misehero-{env} && git status --porcelain"
```

- If the server has uncommitted changes, **warn the user** and ask whether to `git stash` them before proceeding.
- If SSH fails, stop and report the error.

### 3. Show What Will Be Deployed

```bash
# Show commits that will be deployed (server vs origin)
ssh -i .deploy_key deploy@46.101.121.250 "cd /var/www/misehero-{env} && git fetch origin && git log --oneline HEAD..origin/{branch} | head -20"
```

Show the user the list of new commits and **ask for confirmation** before proceeding.

### 4. Update Version & Date

**MANDATORY before every deployment.** Read and update `frontend_demo/version.json`:

1. Read the current `frontend_demo/version.json` to get the current version and date.
2. **Date**: Always update to today's date in `DD.MM.YYYY` format (Czech format).
3. **Version**: Ask the user if the version should be incremented (e.g., `v7` → `v8`). If the user says no or if only minor changes, keep the current version but still update the date.
4. Use the `Edit` tool to update `frontend_demo/version.json` with the new values.
5. **Commit and push** the version change to the target branch before deploying:
   ```bash
   git add frontend_demo/version.json
   git commit -m "chore: update version to {version} ({date})"
   git push origin {branch}
   ```

This ensures the login page and app header show the correct version and deployment date on all environments.

### 5. Execute Deployment

Run the deploy script on the server:

```bash
ssh -i .deploy_key deploy@46.101.121.250 "cd /var/www/misehero-{env} && bash deploy/deploy.sh {env}"
```

This script handles: git pull, pip install, migrations, collectstatic, service restart, and health check.

### 6. Post-deploy Verification

After deployment completes, verify all deployed environments:

```bash
# Health check - verify service is running and API responds
ssh -i .deploy_key deploy@46.101.121.250 "systemctl is-active misehero-{env} && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:{port}/api/v1/"
```

```bash
# Show current deployed commit
ssh -i .deploy_key deploy@46.101.121.250 "cd /var/www/misehero-{env} && git log --oneline -1"
```

```bash
# Verify version.json is correct on server
ssh -i .deploy_key deploy@46.101.121.250 "cat /var/www/misehero-{env}/frontend_demo/version.json"
```

### 7. Update Deployment History

**MANDATORY** — After each environment is deployed (success or failure), append a row to `.claude/deployment_history.md`.

Use the `Edit` tool to append a new row to the table in `.claude/deployment_history.md` with this format:

```
| YYYY-MM-DD HH:MM | {environment} | {version} | {short_hash} {commit_message} | OK/FAIL | Claude Code |
```

- **Date & Time**: Current date and time in `YYYY-MM-DD HH:MM` format (Prague timezone, UTC+1/+2)
- **Environment**: `test`, `stage`, or `production`
- **Version**: From `version.json` (e.g., `v7`)
- **Commit**: Short hash + first line of commit message (e.g., `abc1234 feat: add export`)
- **Status**: `OK` if deployment succeeded and health check passed, `FAIL` if any step failed
- **Deployed By**: `Claude Code`

Example row:
```
| 2026-03-19 18:30 | test | v7 | abc1234 feat: add new field | OK | Claude Code |
```

### 8. Report Results

Print a summary table:

| Environment | Status | HTTP Code | Version | Date | Deployed Commit |
|-------------|--------|-----------|---------|------|-----------------|
| {env}       | OK/FAIL| 200/xxx   | v7      | 19.03.2026 | abc1234 message |

## Safety Rules

- **NEVER deploy to production without explicit user confirmation.**
- If deploying `all`, always deploy in order: test → stage → production.
- If any environment fails, **stop** and report — do not continue to the next environment.
- If the server has local changes, always ask before stashing.
- Always show what commits will be deployed before executing.
- **Always update version.json date before deploying.**
- **Always update deployment history**, even for failed deployments.
- **Always verify version.json on server** after deployment.
- If the deploy script fails (non-zero exit), show the last 30 lines of the service journal:
  ```bash
  ssh -i .deploy_key deploy@46.101.121.250 "sudo journalctl -u misehero-{env} --no-pager -n 30"
  ```
