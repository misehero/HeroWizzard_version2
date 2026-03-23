---
name: release
description: Orchestrate a full release workflow — bump version, commit, push, deploy through environments, run tests, and verify. Use for new version releases.
disable-model-invocation: true
argument-hint: "v9|v10|..."
---

# Release Workflow — Mise HERo Finance

Orchestrate a complete version release through all environments.

**New version:** `$ARGUMENTS` (e.g., `v9`)

## Overview

A release follows this pipeline:

```
develop → test (deploy + test) → stage (merge + deploy + test) → production (merge + deploy + verify)
```

Each gate must pass before proceeding to the next.

## Steps

### 1. Validate Arguments

- `$ARGUMENTS` must be a version string like `v9`, `v10`, etc.
- If empty, read current version from `frontend_demo/version.json` and suggest the next increment.

### 2. Pre-release Checklist

Before starting, verify:

```bash
# Check current branch
git branch --show-current

# Check for uncommitted changes
git status --porcelain

# Check current version
cat frontend_demo/version.json
```

**Requirements:**
- Working directory must be clean (no uncommitted changes)
- Must be on `develop` branch (or confirm intent if on another branch)
- Display the current version and confirm the new version with the user

### 3. Version Bump

Update `frontend_demo/version.json`:

```json
{
  "version": "{NEW_VERSION}",
  "date": "{TODAY_DD.MM.YYYY}"
}
```

Commit and push:
```bash
git add frontend_demo/version.json
git commit -m "chore: bump version to {NEW_VERSION}"
git push origin develop
```

### 4. Gate 1 — Deploy to TEST

```
/deploy test
```

After deploy completes, run tests:

```
/test test
```

**Gate check:** If tests fail, STOP and report. Do not proceed to stage.

Ask user: "Test environment passed. Proceed to stage?"

### 5. Gate 2 — Merge to stage & Deploy

```bash
# Merge develop → stage
git checkout stage
git pull origin stage
git merge develop --no-edit
git push origin stage

# Return to develop
git checkout develop
```

Then deploy:
```
/deploy stage
```

Run tests:
```
/test stage
```

**Gate check:** If tests fail, STOP and report. Do not proceed to production.

Ask user: "Stage environment passed. Proceed to production? (This requires DEPLOY confirmation)"

### 6. Gate 3 — Merge to production & Deploy

```bash
# Merge stage → production
git checkout production
git pull origin production
git merge stage --no-edit
git push origin production

# Return to develop
git checkout develop
```

Then deploy (includes mandatory DEPLOY confirmation):
```
/deploy production
```

### 7. Post-release Verification

Run a quick health check on all environments:
```
/status all
```

### 8. Release Summary

Print a final summary:

```
## Release {NEW_VERSION} — Complete

| Step                    | Status |
|------------------------|--------|
| Version bump           | ✅     |
| Deploy to test         | ✅     |
| Tests on test          | ✅     |
| Merge develop → stage  | ✅     |
| Deploy to stage        | ✅     |
| Tests on stage         | ✅     |
| Merge stage → prod     | ✅     |
| Deploy to production   | ✅     |
| All environments healthy| ✅    |

Environments:
- test:       {version} @ {commit}
- stage:      {version} @ {commit}
- production: {version} @ {commit}
```

### 9. Update main branch

After a successful production release, sync main:

```bash
git checkout main
git pull origin main
git merge production --no-edit
git push origin main
git checkout develop
```

## Partial Releases

If the user only wants to release to a specific environment:
- `release v9 to stage` — stops after stage gate
- `release v9 to test` — stops after test gate

Parse the arguments accordingly.

## Rollback

If any gate fails:
1. Report exactly what failed and why
2. Do NOT proceed to the next environment
3. Suggest fixes or manual rollback steps
4. The user can re-run `/release` after fixing

## Safety Rules

- **Never skip gates** — each environment must pass before proceeding
- **Always ask for confirmation** between environments
- **Production requires DEPLOY confirmation** (enforced by deploy skill)
- **Never force-push** to any branch
- If merge conflicts occur, STOP and ask the user to resolve them
- Always return to `develop` branch at the end, regardless of outcome
