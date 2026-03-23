---
name: deploy
description: Deploy Mise HERo Finance to DigitalOcean droplet environments (test, stage, production). Use when the user wants to deploy, push to server, or update environments.
disable-model-invocation: true
argument-hint: "test|stage|production|all"
---

# Deploy Mise HERo Finance

Deploy to DigitalOcean droplet at `46.101.121.250` using **environment-specific SSH keys** as user `deploy`.

**Target:** `$ARGUMENTS`

## Environment Map

| Environment | Branch     | Key File               | Server Path                  | Port | Service Name        | URL                                        |
|-------------|-----------|------------------------|------------------------------|------|---------------------|--------------------------------------------|
| test        | develop    | `.deploy_key_test`      | /var/www/misehero-test       | 8001 | misehero-test       | https://test.herowizzard.misehero.cz/      |
| stage       | stage      | `.deploy_key_stage`     | /var/www/misehero-stage      | 8002 | misehero-stage      | https://stage.herowizzard.misehero.cz/     |
| production  | production | `.deploy_key_production`| /var/www/misehero-production | 8003 | misehero-production | https://herowizzard.misehero.cz/           |

**SSH key rule:** Always use the environment-specific key. The legacy shared `.deploy_key` is deprecated and will be removed.

## Version Tracking

Version and date are stored in `frontend_demo/version.json`:
```json
{
  "version": "v9",
  "date": "23.03.2026"
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

### 2. Production Gate (production only)

**CRITICAL:** If deploying to `production` (directly or as part of `all`):

1. **Show what will change** — list all commits since last production deploy
2. **Pre-deploy checklist** — verify:
   - [ ] Tests pass on stage (`/test stage` or manual confirmation from user)
   - [ ] Version is bumped appropriately
   - [ ] No uncommitted changes on production server
3. **Two-step confirmation** — ask the user to type `DEPLOY` to confirm production deployment
4. **If user does not confirm**, skip production and report

This gate is **mandatory**. Do NOT proceed to production without explicit `DEPLOY` confirmation.

### 3. Pre-flight Checks

Before deploying each environment, run these checks using the **environment-specific key**:

```bash
# Check SSH connectivity
ssh -i .deploy_key_{env} -o ConnectTimeout=5 deploy@46.101.121.250 "echo 'SSH OK'"
```

```bash
# Check current status of the target service
ssh -i .deploy_key_{env} deploy@46.101.121.250 "systemctl is-active misehero-{env} && echo 'Service running' || echo 'Service NOT running'"
```

```bash
# Check for uncommitted changes on the server
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && git status --porcelain"
```

```bash
# Check for deployment lock
ssh -i .deploy_key_{env} deploy@46.101.121.250 "test -f /tmp/misehero-deploy-{env}.lock && echo 'LOCKED by PID '$(cat /tmp/misehero-deploy-{env}.lock) || echo 'No lock'"
```

- If the server has uncommitted changes, **warn the user** and ask whether to `git stash` them before proceeding.
- If SSH fails, stop and report the error.
- If a deploy lock exists and the process is running, **stop** — another deployment is in progress.

### 4. Show What Will Be Deployed

```bash
# Show commits that will be deployed (server vs origin)
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && git fetch origin && git log --oneline HEAD..origin/{branch} | head -20"
```

Show the user the list of new commits and **ask for confirmation** before proceeding (for test/stage, a simple "yes" suffices).

### 5. Update Version & Date

**BLOCKING REQUIREMENT — do NOT skip this step.** Every deployment MUST update `frontend_demo/version.json` before deploying. If you forget this step, the environment will show stale version info.

1. Read the current `frontend_demo/version.json` to get the current version and date.
2. **Date**: **ALWAYS** update to today's date in `DD.MM.YYYY` format (Czech format), even if version stays the same.
3. **Version**: Ask the user if the version should be incremented (e.g., `v8` → `v9`). If the user says no or if only minor changes, keep the current version but still update the date.
4. Use the `Edit` tool to update `frontend_demo/version.json` with the new values.
5. **Commit and push** the version change to the target branch before deploying:
   ```bash
   git add frontend_demo/version.json
   git commit -m "chore: update version to {version} ({date})"
   git push origin {branch}
   ```
6. **Update version tracking files** after successful deployment:
   - **`docs/UPGRADE_GUIDE.md`**: If the version number changed (not just the date), add a new row to the Version History table with the version, date, branch, and key changes.
   - **`.claude/deployment_history.md`**: Always append a row (see step 8 below).

This ensures the login page and app header show the correct version and deployment date on all environments.

### 6. Execute Deployment

Run the deploy script on the server (includes lock, rollback, health check):

```bash
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && bash deploy/deploy.sh {env}"
```

The deploy script (`deploy/deploy.sh` v2) handles:
- **Lock acquisition** — prevents concurrent deploys
- Git pull from the correct branch
- pip install, migrations, collectstatic
- Service restart
- **Health check** with automatic rollback on failure
- **Version verification**

### 7. Post-deploy Verification

After deployment completes, verify all deployed environments:

```bash
# Health check - verify service is running and API responds
ssh -i .deploy_key_{env} deploy@46.101.121.250 "systemctl is-active misehero-{env} && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:{port}/api/v1/"
```

```bash
# Show current deployed commit
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && git log --oneline -1"
```

```bash
# Verify version.json is correct on server
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cat /var/www/misehero-{env}/frontend_demo/version.json"
```

### 8. Update Deployment History

**MANDATORY** — After each environment is deployed (success or failure), append a row to `.claude/deployment_history.md`.

Use the `Edit` tool to append a new row to the table in `.claude/deployment_history.md` with this format:

```
| YYYY-MM-DD HH:MM | {environment} | {version} | {short_hash} {commit_message} | OK/FAIL | Claude Code |
```

- **Date & Time**: Current date and time in `YYYY-MM-DD HH:MM` format (Prague timezone, UTC+1/+2)
- **Environment**: `test`, `stage`, or `production`
- **Version**: From `version.json` (e.g., `v8`)
- **Commit**: Short hash + first line of commit message (e.g., `abc1234 feat: add export`)
- **Status**: `OK` if deployment succeeded and health check passed, `FAIL` if any step failed
- **Deployed By**: `Claude Code`

### 9. Report Results

Print a summary table:

| Environment | Status | HTTP Code | Version | Date       | Deployed Commit     |
|-------------|--------|-----------|---------|------------|---------------------|
| {env}       | OK/FAIL| 200/xxx   | v8      | 21.03.2026 | abc1234 message     |

## Rollback Procedure

If an automatic rollback occurred or you need manual rollback:

```bash
# Check what commit was deployed before
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cat /tmp/misehero-rollback-{env}.txt"

# Manual rollback to specific commit
ssh -i .deploy_key_{env} deploy@46.101.121.250 "cd /var/www/misehero-{env} && git reset --hard {commit_hash} && sudo systemctl restart misehero-{env}"

# Verify after rollback
ssh -i .deploy_key_{env} deploy@46.101.121.250 "systemctl is-active misehero-{env} && cd /var/www/misehero-{env} && git log --oneline -1"
```

## Safety Rules

- **NEVER deploy to production without the two-step `DEPLOY` confirmation.**
- **Always use environment-specific SSH keys** (`.deploy_key_test`, `.deploy_key_stage`, `.deploy_key_production`).
- If deploying `all`, always deploy in order: test → stage → production.
- If any environment fails, **stop** and report — do not continue to the next environment.
- If the server has local changes, always ask before stashing.
- Always show what commits will be deployed before executing.
- **Always update version.json date before deploying.**
- **Always update deployment history**, even for failed deployments.
- **Always verify version.json on server** after deployment.
- If the deploy script fails (non-zero exit), show the last 30 lines of the service journal:
  ```bash
  ssh -i .deploy_key_{env} deploy@46.101.121.250 "sudo journalctl -u misehero-{env} --no-pager -n 30"
  ```
- **Deployment lock**: If a lock exists and PID is active, do NOT force deploy. Wait or ask user.
- **Automatic rollback**: The deploy script will auto-rollback if health check fails. Report this clearly to the user.

## GitHub Actions Secrets (for CI/CD)

Each environment uses its own SSH key secret in GitHub:

| Secret Name          | Environment | Description                    |
|---------------------|-------------|--------------------------------|
| `DO_HOST`           | all         | `46.101.121.250`              |
| `DO_SSH_USER`       | all         | `deploy`                       |
| `DO_SSH_KEY_TEST`   | test        | Contents of `.deploy_key_test` |
| `DO_SSH_KEY_STAGE`  | stage       | Contents of `.deploy_key_stage`|
| `DO_SSH_KEY_PRODUCTION` | production | Contents of `.deploy_key_production` |

To set up: GitHub repo → Settings → Secrets and variables → Actions → New repository secret.
For environment-specific secrets, create environments (test, stage, production) under Settings → Environments first.
