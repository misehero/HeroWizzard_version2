# Test Scenarios

Manual test checklists by version. Run on stage environment.

## Prerequisites

- Login credentials for all 4 roles: admin, manager, accountant, viewer
- Test CSV files: `docs/test-data/test_creditas.csv`, `docs/test-data/test_raiffeisen.csv`

---

## Test 1: Dashboard Filters — Druh & Detail

1. Login as any user
2. Go to Dashboard
3. Verify **Druh** dropdown is present in filters, grouped by Výdaje/Příjmy
4. Select a Druh value → verify **Detail** dropdown populates with matching options
5. Verify transactions filter correctly when Druh is selected
6. Clear Druh → verify Detail resets to "Vše"

**Expected:** Druh and Detail dropdowns work, data filters correctly.

---

## Test 2: Table Columns — Status & Typ Removed

1. Go to Dashboard
2. Verify table does NOT show "Status" or "Typ" columns
3. Verify remaining columns: Datum, Zdroj, Popis, Protistrana, Částka, P/V, Kategorie, Aktivní, Poslední změna, Edit
4. Verify Status filter still works in the filter bar

**Expected:** Table has 2 fewer columns, Status filter still functional.

---

## Test 3: Manual Transaction — Full Field Editing

1. Click **+ Přidat transakci** → create a manual transaction (no CSV import)
2. Save it
3. Click edit on the newly created transaction
4. Verify bank fields (Datum, Částka, Poznámka, VS, Protistrana, Typ, Měna) are **editable**
5. Modify the amount and date, save
6. Verify changes persisted

**Expected:** Manual transaction bank fields are editable in edit mode.

---

## Test 4: Imported Transaction — Bank Fields Locked

1. Import a CSV file (Creditas or Raiffeisen)
2. Click edit on an imported transaction
3. Verify bank fields (Datum, Částka, etc.) are **disabled/greyed out**
4. Verify app fields (P/V, Druh, KMEN, etc.) are editable

**Expected:** Imported transaction bank fields remain read-only.

---

## Test 5: Status — Admin/Manager Can Edit

1. Login as **admin** (admin@misehero.cz)
2. Edit any transaction
3. Verify **Status dropdown** is visible in the Kategorizace section
4. Change status to "Schváleno", save
5. Verify status persisted
6. Repeat with **manager** role

**Expected:** Admin and manager see Status dropdown and can change it.

---

## Test 6: Status — Accountant Auto-Assign

1. Login as **accountant** (accountant@misehero.cz)
2. Edit any transaction (change Druh or any field)
3. Save
4. Login as admin → find the same transaction
5. Verify status is "Čeká na schválení"
6. Verify accountant does NOT see Status dropdown in edit modal

**Expected:** Accountant saves force status to "Čeká na schválení".

---

## Test 7: Status — Viewer Auto-Assign

1. Login as **viewer** (viewer@misehero.cz)
2. Edit any transaction
3. Save
4. Login as admin → verify status is "Čeká na schválení"

**Expected:** Viewer saves also force "Čeká na schválení".

---

## Test 8: Manual Transaction — Status by Role

1. Login as **accountant**
2. Create a manual transaction (+ Přidat transakci)
3. Login as admin → verify new transaction has status "Čeká na schválení"
4. Login as **admin**, create a manual transaction
5. Verify it has status "Upraveno"

**Expected:** Role determines initial status of manual transactions.

---

## Test 9: Status Filter — New Option

1. Go to Dashboard
2. Open Status filter dropdown
3. Verify "Čeká na schválení" option is present
4. Select it → verify only matching transactions shown

**Expected:** New status appears in filter and works.

---

## Test 10: iDoklad Card Hidden

1. Go to Import CSV page
2. Verify only **Creditas** and **Raiffeisen** cards are visible
3. Verify iDoklad card is hidden
4. Verify layout shows 2 cards side-by-side

**Expected:** iDoklad import card is hidden.

---

## Test 11: Category Rules — Druh/Detail Dropdowns

1. Go to Pravidla kategorií
2. Click **+ Přidat pravidlo**
3. Verify **Nastavit kategorii (Druh)** is a dropdown (not text input), grouped by Výdaje/Příjmy
4. Select a Druh value → verify **Nastavit detail** dropdown populates
5. Verify **Daně** checkbox is hidden
6. Verify **MH%, ŠK%, XP%, FR%** number inputs are present below KMEN

**Expected:** Rule form uses dropdowns for druh/detail, has KMEN pct fields, dane hidden.

---

## Test 12: Category Rules — Save with KMEN Percentages

1. Create a rule with KMEN=MH, MH%=100, ŠK%=0, XP%=0, FR%=0
2. Save → verify rule created
3. Edit the rule → verify KMEN percentage values are populated correctly
4. Apply rules to uncategorized → verify KMEN pct values applied to matching transactions

**Expected:** KMEN percentage fields save and load correctly on rules.

---

## Test 13: CSV Import + Category Rules

1. Create a category rule matching a known test transaction
2. Import `docs/test-data/test_raiffeisen.csv` (delete existing first if needed)
3. Verify matching transaction has rule's values applied automatically

**Expected:** Rules apply during import as before (regression check).

---

## Test 14: Version Check

1. Check bottom of any page or title bar
2. Verify version shows **v8 | 21.03.2026**

**Expected:** Version updated to v8.

---

## v9 Test Scenarios (23.03.2026)

## Test 15: CostDetail Cascading Dropdowns — Transaction Modal

1. Login as admin
2. Edit any transaction (pencil icon)
3. In the modal, select **P/V** = Výdaj (V)
4. Verify **Druh** dropdown shows only Výdaje cost types
5. Select a Druh value → verify **Detail** dropdown populates with matching options
6. Verify **Poznámka** hint appears when a Detail with poznámka is selected
7. Switch P/V to Příjem (P) → verify Druh dropdown changes to Příjmy cost types

**Expected:** Cascading P/V → Druh → Detail → Poznámka works in transaction modal.

---

## Test 16: CostDetail in Číselníky (Lookups)

1. Login as admin, go to Číselníky page
2. Verify **Druhy nákladů** tab is present
3. Verify entries are grouped by Výdaje/Příjmy
4. Click edit on any CostDetail → verify Druh, Detail, Poznámka fields are editable
5. Create a new CostDetail entry → verify it appears in the list
6. Deactivate a CostDetail entry → verify it disappears from the list (unless "show inactive" is on)

**Expected:** Full CRUD for CostDetail in Číselníky page.

---

## Test 17: Backup v6 — CostDetail Included

1. Login as admin
2. Click "Export zálohy" → download backup JSON
3. Open the JSON file → verify `"cost_details"` key exists with entries
4. Verify `"version": 6` in the JSON
5. Import the backup on a fresh environment → verify CostDetail records are restored

**Expected:** Backup includes cost_details, restore works.

---

## v10 Test Scenarios (24.03.2026)

## Test 18: Číselníky Refactoring — No Pagination, Textarea, Deactivate

1. Login as admin, go to Číselníky
2. Verify all lookup items load without pagination (no next/previous buttons)
3. Verify description fields are **resizable textareas** (not single-line inputs)
4. Verify **Typ** dropdown is editable on Products
5. Deactivate an item → verify it shows deactivated state with transaction count
6. Reactivate the item → verify it returns to active state

**Expected:** Číselníky UI improvements work as designed.

---

## Test 19: Module Switcher

1. Login as **admin**
2. Verify a **module switcher dropdown** appears in the navbar
3. Verify it shows 3 options: Finance, Fakturace, Reporty
4. Select different modules → verify navbar items change accordingly
5. Login as **accountant** → verify module switcher is NOT visible (admin-only)

**Expected:** Admin-only module switcher with dynamic navbar.

---

## Test 20: Version Check

1. Check login page or app header
2. Verify version shows **v10 | 24.03.2026**

**Expected:** Version updated to v10.
