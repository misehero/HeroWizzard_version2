# CLAUDE.md — Mise HERo Finance (HeroWizzard)

## What This Is
Django 5.2 REST API + vanilla JS frontend. Czech-language financial transaction management with CSV bank imports, auto-categorization rules, and multi-tribe (KMEN) expense splitting.
Stack: Python 3.11+, PostgreSQL, DRF, Gunicorn, Nginx. Frontend: static HTML/JS/CSS in `frontend_demo/` — no build step, no npm, no framework.

## Owner Context
Developer: Antonín (senior fullstack, 10+ years, university CS/AI background).
Solo project. Working environment: VS Code on Windows 11, SSH to DigitalOcean droplet for deployment.
Claude Code runs locally against the repo, deploys via SSH with per-environment keys.
Planning and architecture review happen on a separate claude.ai account (no shared memory with this instance).

---

## HARD RULES (violating these causes real damage)

### Git — NON-NEGOTIABLE
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- English commit messages, one logical change per commit
- NEVER force push. NEVER push directly to main or production.
- NEVER commit without showing full diff first and getting approval.
- NEVER run `git reset --hard` without explicit approval.
- NEVER commit: `.env`, `.deploy_key*`, API keys, tokens, passwords, `*.pyc`, `nul`
- Branch flow: `develop` → `stage` → `production`. Branch `main` kept in sync with production.
- Always run `git status` + `git diff --staged` before pushing.

### Data Safety
- All DB mutations wrapped in `transaction.atomic()`
- FK relationships use RESTRICT at DB level — use `TRUNCATE ... CASCADE` for bulk wipes
- When adding new models: MUST update `export_backup()`, `import_backup()`, TRUNCATE list, and bump backup version in `apps/transactions/views.py` — forgetting this silently breaks backup/restore
- Never modify migration files that have been applied to any environment
- Never drop or alter columns without explicit approval — data loss is irreversible

### Protected Files — Do NOT Modify Without Explicit Instruction
- `config/settings.py` — changes ripple across all environments
- `deploy/deploy.sh` — battle-tested deploy script with auto-rollback
- `.github/workflows/*.yml` — CI/CD pipelines
- Any applied migration file (`apps/*/migrations/0*.py`)
- `.deploy_key*` files — never read, cat, echo, or display these

---

## Architecture

### Django Apps
- **apps/core/** — User model (email-based, no username), 4 roles (admin, manager, accountant, viewer), JWT auth (60min access, 7d refresh), permissions per role
- **apps/transactions/** — Transaction CRUD, CSV import service (bank + iDoklad), CategoryRule auto-detection, lookup tables (Project, Product, ProductSubgroup, CostDetail), IDokladInvoice, backup/restore, Excel export
- **apps/analytics/** — Placeholder (not implemented)
- **apps/predictions/** — Placeholder (not implemented)

### Model Conventions (enforce on ALL new models)
- UUID primary key, `is_active` BooleanField (soft-delete), `created_at` DateTimeField(auto_now_add), `updated_at` DateTimeField(auto_now)
- **Exceptions:** Lookup models (Project, Product, ProductSubgroup, CostDetail) use CharField slug PKs. CostDetail also missing timestamps. Audit/log models (AuditLog, TransactionAuditLog, ImportBatch) lack is_active. IDokladInvoice lacks is_active and updated_at.
- **Transaction special case:** has BOTH `is_active` (exclude from exports) AND `is_deleted` (true soft-delete, excluded from all views)

### ViewSet Conventions
- Filter `is_active=True` on `list` action ONLY (so detail/update/delete work on inactive records)
- Soft-delete: set `is_active=False`, return 204
- Lookup ViewSets (Project, Product, ProductSubgroup, CostDetail): `pagination_class = None` — return all items
- TransactionViewSet: standard DRF pagination (50 items/page)
- All endpoints under `/api/v1/`

### Key Domain Rules
- **KMEN split:** `mh_pct + sk_pct + xp_pct + fr_pct` must equal exactly 100, or ALL must be 0. Validated in `Transaction.clean()`.
- **Category rules:** 6-level match hierarchy (protiúčet → merchant → VS → typ → město → keyword), first match wins GLOBALLY. Full spec: `docs/CATEGORY_RULES.md`.
- **CSV import:** Auto-detects bank format (Creditas, Raiffeisen, generic) from headers. Czech format: semicolon delimiter, comma decimal, DD.MM.YYYY, cp1250/utf-8-sig encoding.
- **Transaction fields:** 22 bank columns (read-only after import) + 17 app columns (user-editable). Manual transactions have all fields editable.
- **Status workflow:** 6 statuses: Importováno → Zpracováno → Schváleno + Upraveno, Čeká na schválení, Chyba. Accountant/viewer saves force "Čeká na schválení". Admin/manager can set any status.

---

## Environments

| Env | Branch | Domain | Service | DB | Port |
|-----|--------|--------|---------|-----|------|
| test | develop | test.herowizzard.misehero.cz | misehero-test | misehero_test | 8001 |
| stage | stage | stage.herowizzard.misehero.cz | misehero-stage | misehero_stage | 8002 |
| prod | production | herowizzard.misehero.cz | misehero-production | misehero_production | 8003 |

**Server:** 46.101.121.250 (Ubuntu 24.04, 2GB RAM, 1 vCPU)
**SSH:** user `deploy`, per-env keys: `.deploy_key_test`, `.deploy_key_stage`, `.deploy_key_production`
**Legacy:** `.deploy_key` (shared, deprecated — still works, scheduled for removal)
**SSL:** Wildcard cert `*.herowizzard.misehero.cz` via Certbot
**Proxy:** Nginx :443 → Gunicorn 127.0.0.1:{port}
**Backups:** Daily automated JSON backups via systemd timers, 30-day retention at `/var/www/misehero-{env}/backups/`

---

## Commands

```bash
# Local development
python manage.py runserver                     # dev server at :8000
python manage.py migrate                       # apply migrations
python manage.py seed_lookups                  # seed Project/Product/CostDetail
python manage.py createsuperuser               # create admin user
python manage.py apply_rules                   # run category rules on existing transactions
python manage.py backup_to_json                # manual JSON backup
python manage.py import_csv <file>             # CLI CSV import
python manage.py import_cost_details <file>    # import Druh/Detail from Excel
cd frontend_demo && python -m http.server 5173 # serve frontend (separate terminal)

# Testing
pytest                                         # all tests
pytest apps/transactions/tests/ -v             # transaction tests
pytest -x -q                                   # stop on first failure, quiet
pytest --cov=apps --cov-report=term-missing    # with coverage

# Code quality
black apps/ config/ && isort apps/ config/     # format
black --check apps/ config/                    # check only

# Deployment (via SSH to droplet)
ssh -i .deploy_key_{env} deploy@46.101.121.250 \
  "cd /var/www/misehero-{env} && bash deploy/deploy.sh {env}"
```

### Custom Slash Commands (`.claude/skills/`)
- `/deploy {env|all}` — full deploy with pre-flight, confirmation gate, health check, auto-rollback. Production requires typing DEPLOY.
- `/status {env|all}` — read-only health check: API, service, DB, backup age, SSL expiry, disk space
- `/release` — version bump and release workflow
- `/test {env}` — run integration test suite against a live environment

### Hooks (`.claude/hooks/`)

- **Auto-format hook:** Python files are auto-formatted with black + isort after every Write/Edit
- **Protected files hook:** `config/settings.py`, `deploy/deploy.sh`, `.github/workflows/`, `.deploy_key*`, `.env`, and applied migrations are blocked from editing without explicit permission (exit 2 = hard block)
- **Large file warning:** Files over 500 lines trigger a warning suggesting line-range reads to save tokens
- Hook config lives in `.claude/settings.json` (committed), scripts in `.claude/hooks/` (committed)
- To temporarily disable all hooks: add `"disableAllHooks": true` to settings.json

---

## Task Execution Preferences

### When to Plan First (use "plan:" prefix or ask to plan before executing)
- Any change touching 3+ files
- New features requiring model + serializer + view + frontend + tests
- Refactoring across multiple modules
- Architecture decisions with multiple valid approaches
- Anything involving migrations (irreversible once applied)

### When Direct Execution Is Fine
- Single-file bug fixes with obvious cause
- Adding a field to one model (single migration)
- Formatting, linting
- Running commands, checking status, reading files

### Token Efficiency — IMPORTANT (budget is limited)
- Do NOT scan entire directories speculatively — read specific files named in the task
- When context is needed, read the relevant `docs/*.md` file rather than exploring source code
- For simple tasks (formatting, single-field changes, config): suggest switching to Sonnet model
- Prefer focused, single-purpose sessions over long multi-goal sessions
- If a task requires 10+ file edits, decompose into subtasks and confirm plan first
- Avoid re-reading files already discussed in the current session
- When showing diffs, show only changed sections, not entire files

### Communication Style
- Reference design patterns by name (Repository, Strategy, Observer, etc.)
- When proposing a solution, explain why alternatives are worse
- Flag overengineered solutions — simpler wins when it meets requirements
- ~10% educational content: connect current task to broader CS/architecture concepts
- Constructive criticism welcome — tell me when I'm doing something suboptimal
- After completing a task: brief summary of what changed + any follow-up items needed

---

## Current State (v10, 24.03.2026)

### What's Built and Working
- CSV import: Creditas + Raiffeisen with auto-format detection
- Category rules: 6-level hierarchy, exact/contains/starts_with matching, 3 modes
- Transaction CRUD with role-based status workflow (4 roles)
- CostDetail: 105 Druh/Detail combinations, cascading dropdowns (P/V → Druh → Detail → Poznámka)
- Číselníky refactoring: resizable textareas, editable Typ dropdown, in-place deactivate/reactivate with counts
- Module switcher: admin-only dropdown (Finance/Fakturace/Reporty), dynamic navbar from centralized MODULES config
- Backup/restore v6 (transactions, rules, batches, audit logs, all lookups, cost_details)
- Daily automated backups (systemd timers, 30-day retention, all 3 environments)
- Multi-env deploy: per-env SSH keys, deploy locks, auto-rollback on health check failure
- CI/CD: GitHub Actions per branch (push to develop → test, push to stage → stage, push to production → prod with approval)
- Frontend pages: login, dashboard, upload CSV, category rules, lookups (admin), users (admin), help

### Active Development / Next Up
1. iDoklad Module 2: VS matching between invoices and bank transactions (Module 1 = CSV import done)
2. Email setup via Resend (HTTP API, bypasses DigitalOcean SMTP block) — see `docs/email-setup.md`
3. Backup validation: corruption/error detection, improved error management and logging
4. Regression test suite: automated tests per version ensuring previous functionality still works
5. Audit log improvements and better error handling

### Known Tech Debt
- CostDetail model: missing created_at, updated_at fields
- Frontend: no cache-busting — users need Ctrl+Shift+R after deploy
- Server: no swap on 2GB droplet — OOM risk under heavy load
- Creditas CSV: no transaction ID field — re-imports create duplicates (documented, by design)
- `frontend/` directory: unused React skeleton — verify nothing references it, then remove

---

## Reference Documentation

Read these on-demand when a task involves their domain. Do NOT load preemptively.

| File | When to read |
|------|-------------|
| `docs/CATEGORY_RULES.md` | Modifying rule logic, adding match types, debugging rule application |
| `docs/CSV_IMPORT_GUIDE.md` | Changing import service, adding bank format, fixing parsing |
| `docs/DEPLOYMENT.md` | Deploy procedures, SSH keys, infrastructure, CI/CD workflows |
| `docs/UPGRADE_GUIDE.md` | Version history, backup format changes, env promotion procedures |
| `docs/iDoklad.md` | iDoklad integration (Module 1 done, Module 2: VS matching planned) |
| `docs/email-setup.md` | Resend email integration plan (not yet implemented) |
| `docs/USER_GUIDE.md` | Current UX behavior, user-facing features, field descriptions |
| `docs/TRANSLATION_MAP.md` | Czech translations, DB field → UI label mapping |
| `docs/TEST_SCENARIOS.md` | Manual test checklists per version |
| `docs/TEST_ACCOUNTS.md` | Test environment credentials (TEST env only, simple passwords) |
| `docs/DEV_SETUP.md` | Local development & testing guide (includes Windows tips) |
| `docs/TEST_REPORT.md` | Test execution results and reports |
| `.claude/deployment_security_strategy.md` | Security enhancements roadmap and status |
| `.claude/deployment_history.md` | Deployment audit trail |
