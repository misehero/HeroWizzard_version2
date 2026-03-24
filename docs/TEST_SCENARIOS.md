# v8 Test Scenarios

Manual test checklist for verifying v8 changes on stage environment.

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
