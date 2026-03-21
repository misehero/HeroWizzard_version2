---
name: test
description: Run automated integration tests against a Mise HERo Finance environment (test, stage, production). Executes the full test suite and reports results.
disable-model-invocation: true
argument-hint: [test|stage|production]
---

# Run Automated Tests — Mise HERo Finance

Execute the full automated integration test suite against a live environment and report results.

**Target environment:** `$ARGUMENTS`

## Environment Map

| Environment | API Base URL                                              | Frontend URL                                  |
|-------------|----------------------------------------------------------|-----------------------------------------------|
| test        | https://test.herowizzard.misehero.cz/api/v1              | https://test.herowizzard.misehero.cz/         |
| stage       | https://stage.herowizzard.misehero.cz/api/v1             | https://stage.herowizzard.misehero.cz/        |
| production  | https://herowizzard.misehero.cz/api/v1                   | https://herowizzard.misehero.cz/              |

## Steps

### 1. Validate Arguments

- If `$ARGUMENTS` is empty, **default to `stage`**.
- Valid values: `test`, `stage`, `production`.
- If `production` is requested, **warn the user** that tests will create and delete transactions on the production database. Ask for confirmation before proceeding.

### 2. Pre-flight Check

Verify the target environment is reachable:

```bash
# Check API is responding
curl -sk -o /dev/null -w "%{http_code}" {API_BASE_URL}/auth/token/
```

If the API returns a non-2xx/405 response, stop and report the environment is unreachable.

### 3. Run the Test Suite

Execute the integration tests using pytest with the target environment URL:

```bash
STAGE_API_URL="{API_BASE_URL}" python -m pytest tests/test_v8_stage.py -v --tb=short 2>&1
```

**Environment variable:** `STAGE_API_URL` overrides the default base URL in the test file.

### 4. Analyze Results

After tests complete:

1. **Count results:** total, passed, failed, skipped, errors
2. **For any failures:** read the failure output carefully and diagnose the root cause
3. **Categorize failures:**
   - **Environment issue** (service down, SSL, network) — suggest re-running or checking the service
   - **Code regression** — identify which feature broke and which files likely need fixing
   - **Test data issue** (e.g., no imported transactions) — note as expected skip
   - **Test bug** — if the test itself has a logic error

### 5. Report Results

Print a clear summary table:

```
## Test Results — {environment}

| Category          | Count |
|-------------------|-------|
| Total             | XX    |
| Passed            | XX    |
| Failed            | XX    |
| Skipped           | XX    |
| Errors            | XX    |

### Failed Tests (if any)
| Test | Error | Likely Cause |
|------|-------|--------------|
| ... | ... | ... |
```

### 6. Recommendations

If there are failures:
- Suggest specific fixes with file paths and line numbers
- If it's a regression, identify the likely commit or change that caused it
- Offer to fix the issues if they are code bugs

If all tests pass:
- Confirm the environment is healthy
- Note any skipped tests and why (e.g., "no imported transactions on stage")

## Test Coverage

The test suite (`tests/test_v8_stage.py`) covers these areas:

### v8 Feature Tests
1. **CostDetail API** — endpoint returns data with druh_type/druh_value
2. **Druh/Detail filters** — filtering transactions by druh and detail
3. **Table columns** — API returns status field (removed from table, kept in API)
4. **Manual transaction editing** — create + edit bank fields on manual transactions
5. **Imported transaction protection** — bank fields locked on imported transactions
6. **Status editing** — admin/manager can change status via dropdown
7. **Status auto-assign (accountant)** — saves force "Čeká na schválení"
8. **Status auto-assign (viewer)** — saves force "Čeká na schválení"
9. **Manual transaction status by role** — admin gets "upraveno", accountant/viewer get "čeká na schválení"
10. **Status filter** — "ceka_na_schvaleni" is a valid filter value
11. **iDoklad endpoint** — upload endpoint exists (returns 401 without auth or 4xx with)
12. **Category rules — druh dropdown** — rules support druh from CostDetail
13. **Category rules — KMEN percentages** — rules support MH/ŠK/XP/FR percentage fields
14. **Apply rules** — apply rules to uncategorized endpoint works
15. **Version check** — version.json matches expected version

### Core Feature Tests
16. **Authentication** — JWT login for all 4 roles (admin, manager, accountant, viewer)
17. **Transaction CRUD** — create, read, update, delete operations
18. **Filters** — account, counterparty, date range, text search filters
19. **CSV Import** — upload endpoint accessible
20. **Lookup tables** — projects, products, subgroups, cost-details endpoints
21. **Permissions** — role-based access control enforcement
22. **KMEN validation** — percentage split must sum to 100% or all be 0

## Safety Rules

- **Never skip SSL verification warnings in output** — note them but don't treat as failures
- Tests create temporary transactions and clean them up — monitor for cleanup failures
- If a test creates data but fails to clean up, note the orphaned transaction IDs in the report
- **Production tests:** always ask for explicit confirmation before running
