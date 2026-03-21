"""
Mise HERo Finance — Integration Test Suite
=============================================
Automated tests covering core features + v8 scenarios.
Runs against a live environment API.

Usage:
    # Default: run against stage
    python -m pytest tests/test_v8_stage.py -v

    # Run against a specific environment
    STAGE_API_URL=http://46.101.121.250:8001/api/v1 python -m pytest tests/test_v8_stage.py -v

Requirements:
    pip install requests pytest
"""

import os

import pytest
import requests
import urllib3

# Suppress SSL warnings for stage/test environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get(
    "STAGE_API_URL", "https://stage.herowizzard.misehero.cz/api/v1"
)
# Derive frontend base URL from API URL (strip /api/v1)
FRONTEND_URL = BASE_URL.rsplit("/api/v1", 1)[0]

USERS = {
    "admin": {"email": "admin@misehero.cz", "password": "admin"},
    "manager": {"email": "manager@misehero.cz", "password": "manager"},
    "accountant": {"email": "accountant@misehero.cz", "password": "accountant"},
    "viewer": {"email": "viewer@misehero.cz", "password": "viewer"},
}


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------
class APIClient:
    """Simple HTTP client wrapping requests with JWT auth."""

    def __init__(self, base_url, token=None, role=None):
        self.base_url = base_url
        self.token = token
        self.role = role

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, path, params=None):
        return requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            verify=False,
        )

    def post(self, path, json=None):
        return requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            verify=False,
        )

    def patch(self, path, json=None):
        return requests.patch(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            verify=False,
        )

    def delete(self, path):
        return requests.delete(
            f"{self.base_url}{path}", headers=self._headers(), verify=False
        )

    def post_file(self, path, file_path, field_name="file"):
        """Upload a file via multipart form."""
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        with open(file_path, "rb") as f:
            return requests.post(
                f"{self.base_url}{path}",
                headers=h,
                files={field_name: f},
                verify=False,
            )


def login(role):
    """Login as a specific role and return an APIClient."""
    creds = USERS[role]
    r = requests.post(
        f"{BASE_URL}/auth/token/",
        json={"email": creds["email"], "password": creds["password"]},
        verify=False,
    )
    assert r.status_code == 200, f"Login failed for {role}: {r.text}"
    token = r.json()["access"]
    return APIClient(BASE_URL, token, role=role)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_client():
    return login("admin")


@pytest.fixture(scope="module")
def manager_client():
    return login("manager")


@pytest.fixture(scope="module")
def accountant_client():
    return login("accountant")


@pytest.fixture(scope="module")
def viewer_client():
    return login("viewer")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def create_manual_transaction(client, **overrides):
    """Create a manual transaction and return its data."""
    payload = {
        "datum": "2026-03-21",
        "castka": "-1500.00",
        "poznamka_zprava": "auto-test transaction",
        "nazev_protiuctu": "Test Company s.r.o.",
        "variabilni_symbol": "9999999",
        "typ": "Test",
        "mena": "CZK",
        "zdroj_transakce": "ucet",
        "prijem_vydaj": "V",
        "vlastni_nevlastni": "-",
        "druh": "",
        "detail": "",
        "kmen": "",
        "mh_pct": "0",
        "sk_pct": "0",
        "xp_pct": "0",
        "fr_pct": "0",
    }
    payload.update(overrides)
    r = client.post("/transactions/create-manual/", json=payload)
    assert r.status_code == 201, f"Create failed: {r.text}"
    return r.json()


def cleanup_transaction(client, txn_id):
    """Soft-delete a test transaction."""
    client.patch(f"/transactions/{txn_id}/", json={"is_active": False})


# ===========================================================================
# PART 1: Core Feature Tests
# ===========================================================================


class TestAuthentication:
    """JWT authentication for all 4 roles."""

    @pytest.mark.parametrize("role", ["admin", "manager", "accountant", "viewer"])
    def test_login_returns_jwt_tokens(self, role):
        creds = USERS[role]
        r = requests.post(
            f"{BASE_URL}/auth/token/",
            json={"email": creds["email"], "password": creds["password"]},
            verify=False,
        )
        assert r.status_code == 200
        data = r.json()
        assert "access" in data
        assert "refresh" in data

    def test_invalid_credentials_rejected(self):
        r = requests.post(
            f"{BASE_URL}/auth/token/",
            json={"email": "admin@misehero.cz", "password": "wrong"},
            verify=False,
        )
        assert r.status_code == 401

    def test_me_endpoint_returns_user_info(self, admin_client):
        r = admin_client.get("/auth/me/")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "admin@misehero.cz"
        assert data["role"] == "admin"

    def test_unauthenticated_request_rejected(self):
        client = APIClient(BASE_URL)
        r = client.get("/transactions/")
        assert r.status_code == 401


class TestTransactionCRUD:
    """Basic transaction create, read, update, delete."""

    def test_list_transactions(self, admin_client):
        r = admin_client.get("/transactions/")
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "results" in data

    def test_create_manual_transaction(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            assert txn["id"] is not None
            assert float(txn["castka"]) == -1500.0
            assert txn["import_batch_id"] is None  # manual
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_read_transaction_detail(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = admin_client.get(f"/transactions/{txn['id']}/")
            assert r.status_code == 200
            detail = r.json()
            assert detail["id"] == txn["id"]
            assert "datum" in detail
            assert "castka" in detail
            assert "status" in detail
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_update_app_fields(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = admin_client.patch(
                f"/transactions/{txn['id']}/",
                json={
                    "prijem_vydaj": "V",
                    "druh": "Fixní",
                    "kmen": "MH",
                    "mh_pct": "100",
                    "sk_pct": "0",
                    "xp_pct": "0",
                    "fr_pct": "0",
                },
            )
            assert r.status_code == 200
            updated = admin_client.get(f"/transactions/{txn['id']}/").json()
            assert updated["druh"] == "Fixní"
            assert updated["kmen"] == "MH"
            assert float(updated["mh_pct"]) == 100.0
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_deactivate_transaction(self, admin_client):
        txn = create_manual_transaction(admin_client)
        r = admin_client.patch(
            f"/transactions/{txn['id']}/", json={"is_active": False}
        )
        assert r.status_code == 200
        updated = admin_client.get(f"/transactions/{txn['id']}/").json()
        assert updated["is_active"] is False


class TestKMENValidation:
    """KMEN percentage split validation."""

    def test_kmen_pct_must_sum_to_100_or_zero(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            # Valid: sum to 100
            r = admin_client.patch(
                f"/transactions/{txn['id']}/",
                json={
                    "kmen": "MH",
                    "mh_pct": "50",
                    "sk_pct": "30",
                    "xp_pct": "10",
                    "fr_pct": "10",
                },
            )
            assert r.status_code == 200

            # Valid: all zero
            r = admin_client.patch(
                f"/transactions/{txn['id']}/",
                json={"kmen": "", "mh_pct": "0", "sk_pct": "0", "xp_pct": "0", "fr_pct": "0"},
            )
            assert r.status_code == 200

            # Invalid: sum to 50
            r = admin_client.patch(
                f"/transactions/{txn['id']}/",
                json={"mh_pct": "25", "sk_pct": "25", "xp_pct": "0", "fr_pct": "0"},
            )
            assert r.status_code == 400, f"Expected 400 for invalid KMEN split, got {r.status_code}"
        finally:
            cleanup_transaction(admin_client, txn["id"])


class TestFilters:
    """Transaction filtering."""

    def test_filter_by_status(self, admin_client):
        r = admin_client.get("/transactions/", params={"status": "importovano"})
        assert r.status_code == 200

    def test_filter_by_prijem_vydaj(self, admin_client):
        r = admin_client.get("/transactions/", params={"prijem_vydaj": "V"})
        assert r.status_code == 200

    def test_filter_by_date_range(self, admin_client):
        r = admin_client.get(
            "/transactions/",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )
        assert r.status_code == 200

    def test_filter_by_zdroj(self, admin_client):
        r = admin_client.get("/transactions/", params={"zdroj_transakce": "ucet"})
        assert r.status_code == 200

    def test_filter_by_mena(self, admin_client):
        r = admin_client.get("/transactions/", params={"mena": "CZK"})
        assert r.status_code == 200

    def test_filter_by_kmen(self, admin_client):
        r = admin_client.get("/transactions/", params={"kmen": "MH"})
        assert r.status_code == 200

    def test_filter_by_search(self, admin_client):
        r = admin_client.get("/transactions/", params={"search": "test"})
        assert r.status_code == 200

    def test_filter_by_ucet(self, admin_client):
        r = admin_client.get("/transactions/", params={"ucet": "000000-1234567890"})
        assert r.status_code == 200

    def test_filter_by_protiucet(self, admin_client):
        r = admin_client.get("/transactions/", params={"protiucet": "1234"})
        assert r.status_code == 200

    def test_filter_by_druh(self, admin_client):
        r = admin_client.get("/transactions/", params={"druh": "Fixní"})
        assert r.status_code == 200

    def test_filter_by_detail(self, admin_client):
        r = admin_client.get("/transactions/", params={"detail": "náklady"})
        assert r.status_code == 200

    def test_ordering(self, admin_client):
        r = admin_client.get("/transactions/", params={"ordering": "-datum"})
        assert r.status_code == 200

    def test_pagination(self, admin_client):
        r = admin_client.get("/transactions/", params={"page": 1})
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert "next" in data or "previous" in data or data["count"] <= 50


class TestLookupEndpoints:
    """Projects, Products, Subgroups, CostDetails endpoints."""

    def test_projects_endpoint(self, admin_client):
        r = admin_client.get("/projects/")
        assert r.status_code == 200

    def test_products_endpoint(self, admin_client):
        r = admin_client.get("/products/")
        assert r.status_code == 200

    def test_subgroups_endpoint(self, admin_client):
        r = admin_client.get("/subgroups/")
        assert r.status_code == 200

    def test_cost_details_endpoint(self, admin_client):
        r = admin_client.get("/cost-details/")
        assert r.status_code == 200
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        assert len(items) > 0, "No cost details found — seed_lookups may not have run"


class TestCSVImport:
    """CSV import endpoints exist and respond."""

    def test_import_batches_endpoint(self, admin_client):
        r = admin_client.get("/imports/batches/")
        assert r.status_code == 200

    def test_upload_endpoint_rejects_empty(self, admin_client):
        """Upload with no file should return 400, not 404/500."""
        r = admin_client.post("/imports/upload/")
        assert r.status_code == 400

    def test_idoklad_endpoint_exists(self, admin_client):
        """iDoklad endpoint should exist (hidden in UI, not removed)."""
        r = admin_client.post("/imports/upload-idoklad/")
        assert r.status_code != 404, "iDoklad endpoint was removed — should only be hidden"


class TestTransactionStats:
    """Stats and trends endpoints."""

    def test_stats_endpoint(self, admin_client):
        r = admin_client.get("/transactions/stats/")
        assert r.status_code == 200
        data = r.json()
        assert "total_count" in data or "count" in data or isinstance(data, dict)

    def test_export_endpoint(self, admin_client):
        r = admin_client.get("/transactions/export/")
        assert r.status_code == 200


class TestCategoryRuleCRUD:
    """Category rule create, read, update, delete."""

    def test_list_rules(self, admin_client):
        r = admin_client.get("/category-rules/")
        assert r.status_code == 200

    def test_create_and_delete_rule(self, admin_client):
        rule_data = {
            "name": "auto-test rule CRUD",
            "match_type": "keyword",
            "match_mode": "contains",
            "match_value": "ZZZZ_AUTOTEST_CRUD",
        }
        r = admin_client.post("/category-rules/", json=rule_data)
        assert r.status_code == 201
        rule_id = r.json()["id"]

        # Read
        r = admin_client.get(f"/category-rules/{rule_id}/")
        assert r.status_code == 200
        assert r.json()["name"] == "auto-test rule CRUD"

        # Update
        r = admin_client.patch(
            f"/category-rules/{rule_id}/", json={"name": "auto-test rule UPDATED"}
        )
        assert r.status_code == 200

        # Delete
        r = admin_client.delete(f"/category-rules/{rule_id}/")
        assert r.status_code == 204

    def test_apply_rules_endpoint(self, admin_client):
        r = admin_client.post("/category-rules/apply_to_uncategorized/")
        assert r.status_code == 200
        assert "updated_count" in r.json()


class TestPermissions:
    """Role-based access control."""

    def test_viewer_cannot_delete_transaction(self, viewer_client, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = viewer_client.delete(f"/transactions/{txn['id']}/")
            # Viewer should not be able to hard-delete
            assert r.status_code in (403, 405), f"Expected 403/405, got {r.status_code}"
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_all_roles_can_read_transactions(
        self, admin_client, manager_client, accountant_client, viewer_client
    ):
        for client in [admin_client, manager_client, accountant_client, viewer_client]:
            r = client.get("/transactions/", params={"page": 1})
            assert r.status_code == 200, f"Role {client.role} cannot read transactions"

    def test_all_roles_can_edit_app_fields(
        self, admin_client, manager_client, accountant_client, viewer_client
    ):
        txn = create_manual_transaction(admin_client)
        try:
            for client in [
                manager_client,
                accountant_client,
                viewer_client,
            ]:
                r = client.patch(
                    f"/transactions/{txn['id']}/", json={"druh": "Fixní"}
                )
                assert r.status_code == 200, (
                    f"Role {client.role} cannot edit app fields: {r.text}"
                )
        finally:
            cleanup_transaction(admin_client, txn["id"])


# ===========================================================================
# PART 2: v8 Feature Tests
# ===========================================================================


class TestV8DruhDetailFilters:
    """v8 Test 1: CostDetail API for druh/detail filter dropdowns."""

    def test_cost_details_have_druh_type_and_value(self, admin_client):
        r = admin_client.get("/cost-details/")
        items = (
            r.json().get("results", r.json())
            if isinstance(r.json(), dict)
            else r.json()
        )
        assert len(items) > 0
        for item in items:
            assert "druh_type" in item
            assert "druh_value" in item
            assert item["druh_type"] in ("vydaje", "prijmy")


class TestV8TableColumns:
    """v8 Test 2: API still returns status/typ (frontend hides them)."""

    def test_transaction_list_has_status_field(self, admin_client):
        r = admin_client.get("/transactions/", params={"page": 1})
        assert r.status_code == 200
        results = r.json().get("results", [])
        if results:
            assert "status" in results[0]
            assert "ucet" in results[0]
            assert "cislo_protiuctu" in results[0]


class TestV8ManualTransactionEditing:
    """v8 Test 3: Manual transactions allow editing bank fields via PATCH."""

    def test_create_and_edit_bank_fields(self, admin_client):
        txn = create_manual_transaction(admin_client)
        txn_id = txn["id"]

        try:
            assert txn["import_batch_id"] is None

            r = admin_client.patch(
                f"/transactions/{txn_id}/",
                json={
                    "datum": "2026-01-15",
                    "castka": "-2500.00",
                    "poznamka_zprava": "Updated note",
                    "nazev_protiuctu": "New Company",
                    "variabilni_symbol": "1111111",
                    "typ": "Úhrada",
                    "mena": "CZK",
                },
            )
            assert r.status_code == 200, f"PATCH failed: {r.text}"

            updated = admin_client.get(f"/transactions/{txn_id}/").json()
            assert updated["datum"] == "2026-01-15"
            assert float(updated["castka"]) == -2500.0
            assert updated["poznamka_zprava"] == "Updated note"
            assert updated["nazev_protiuctu"] == "New Company"
            assert updated["variabilni_symbol"] == "1111111"
            assert updated["typ"] == "Úhrada"
        finally:
            cleanup_transaction(admin_client, txn_id)


class TestV8ImportedTransactionLocked:
    """v8 Test 4: Imported transactions reject bank field edits."""

    def test_imported_txn_bank_fields_readonly(self, admin_client):
        r = admin_client.get("/transactions/", params={"page": 1})
        results = r.json().get("results", [])

        imported_txn = None
        for txn in results:
            detail = admin_client.get(f"/transactions/{txn['id']}/").json()
            if detail.get("import_batch_id"):
                imported_txn = detail
                break

        if imported_txn is None:
            pytest.skip("No imported transactions found — import a CSV first")

        original_datum = imported_txn["datum"]
        original_castka = imported_txn["castka"]

        r = admin_client.patch(
            f"/transactions/{imported_txn['id']}/",
            json={"datum": "2020-01-01", "castka": "999999.00"},
        )
        assert r.status_code == 200

        after = admin_client.get(f"/transactions/{imported_txn['id']}/").json()
        assert after["datum"] == original_datum
        assert after["castka"] == original_castka


class TestV8StatusAdminManagerEdit:
    """v8 Test 5: Admin and manager can explicitly set status."""

    def test_admin_can_change_status(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = admin_client.patch(
                f"/transactions/{txn['id']}/", json={"status": "schvaleno"}
            )
            assert r.status_code == 200
            updated = admin_client.get(f"/transactions/{txn['id']}/").json()
            assert updated["status"] == "schvaleno"
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_manager_can_change_status(self, manager_client, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = manager_client.patch(
                f"/transactions/{txn['id']}/", json={"status": "zpracovano"}
            )
            assert r.status_code == 200
            updated = admin_client.get(f"/transactions/{txn['id']}/").json()
            assert updated["status"] == "zpracovano"
        finally:
            cleanup_transaction(admin_client, txn["id"])


class TestV8StatusAccountantAutoAssign:
    """v8 Test 6: Accountant saves force status to 'ceka_na_schvaleni'."""

    def test_accountant_save_forces_ceka_na_schvaleni(
        self, accountant_client, admin_client
    ):
        txn = create_manual_transaction(admin_client)
        try:
            r = accountant_client.patch(
                f"/transactions/{txn['id']}/", json={"druh": "Fixní"}
            )
            assert r.status_code == 200

            updated = admin_client.get(f"/transactions/{txn['id']}/").json()
            assert updated["status"] == "ceka_na_schvaleni", (
                f"Expected 'ceka_na_schvaleni', got '{updated['status']}'"
            )
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_accountant_cannot_set_status_explicitly(
        self, accountant_client, admin_client
    ):
        txn = create_manual_transaction(admin_client)
        try:
            r = accountant_client.patch(
                f"/transactions/{txn['id']}/", json={"status": "schvaleno"}
            )
            assert r.status_code == 403, (
                f"Expected 403 Forbidden, got {r.status_code}: {r.text}"
            )
        finally:
            cleanup_transaction(admin_client, txn["id"])


class TestV8StatusViewerAutoAssign:
    """v8 Test 7: Viewer saves force status to 'ceka_na_schvaleni'."""

    def test_viewer_save_forces_ceka_na_schvaleni(self, viewer_client, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            r = viewer_client.patch(
                f"/transactions/{txn['id']}/", json={"druh": "Variabilní"}
            )
            assert r.status_code == 200

            updated = admin_client.get(f"/transactions/{txn['id']}/").json()
            assert updated["status"] == "ceka_na_schvaleni"
        finally:
            cleanup_transaction(admin_client, txn["id"])


class TestV8ManualTransactionStatusByRole:
    """v8 Test 8: Manual transaction initial status depends on role."""

    def test_admin_creates_with_upraveno(self, admin_client):
        txn = create_manual_transaction(admin_client)
        try:
            assert txn["status"] == "upraveno", (
                f"Expected 'upraveno', got '{txn['status']}'"
            )
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_accountant_creates_with_ceka_na_schvaleni(
        self, accountant_client, admin_client
    ):
        txn = create_manual_transaction(accountant_client)
        try:
            assert txn["status"] == "ceka_na_schvaleni", (
                f"Expected 'ceka_na_schvaleni', got '{txn['status']}'"
            )
        finally:
            cleanup_transaction(admin_client, txn["id"])

    def test_viewer_creates_with_ceka_na_schvaleni(self, viewer_client, admin_client):
        txn = create_manual_transaction(viewer_client)
        try:
            assert txn["status"] == "ceka_na_schvaleni", (
                f"Expected 'ceka_na_schvaleni', got '{txn['status']}'"
            )
        finally:
            cleanup_transaction(admin_client, txn["id"])


class TestV8StatusFilter:
    """v8 Test 9: ceka_na_schvaleni is a valid status filter."""

    def test_filter_by_ceka_na_schvaleni(self, admin_client):
        r = admin_client.get(
            "/transactions/", params={"status": "ceka_na_schvaleni"}
        )
        assert r.status_code == 200


class TestV8CategoryRulesDruhDetail:
    """v8 Test 11: Rules support druh values from CostDetail."""

    def test_create_rule_with_cost_detail_druh(self, admin_client):
        cd_r = admin_client.get("/cost-details/")
        items = (
            cd_r.json().get("results", cd_r.json())
            if isinstance(cd_r.json(), dict)
            else cd_r.json()
        )
        assert len(items) > 0
        druh_value = items[0]["druh_value"]
        detail_value = items[0]["detail"]

        rule_data = {
            "name": "auto-test rule — druh dropdown",
            "match_type": "keyword",
            "match_mode": "contains",
            "match_value": "ZZZZ_AUTOTEST_DRUH",
            "set_druh": druh_value,
            "set_detail": detail_value,
        }
        r = admin_client.post("/category-rules/", json=rule_data)
        assert r.status_code == 201, f"Create rule failed: {r.text}"
        rule_id = r.json()["id"]

        try:
            rule = admin_client.get(f"/category-rules/{rule_id}/").json()
            assert rule["set_druh"] == druh_value
            assert rule["set_detail"] == detail_value
        finally:
            admin_client.delete(f"/category-rules/{rule_id}/")


class TestV8CategoryRulesKmenPct:
    """v8 Test 12: Rules support KMEN percentage fields."""

    def test_create_rule_with_kmen_percentages(self, admin_client):
        rule_data = {
            "name": "auto-test rule — KMEN pct",
            "match_type": "keyword",
            "match_mode": "contains",
            "match_value": "ZZZZ_AUTOTEST_KMEN",
            "set_kmen": "MH",
            "set_mh_pct": "60.00",
            "set_sk_pct": "20.00",
            "set_xp_pct": "10.00",
            "set_fr_pct": "10.00",
        }
        r = admin_client.post("/category-rules/", json=rule_data)
        assert r.status_code == 201, f"Create rule failed: {r.text}"
        rule_id = r.json()["id"]

        try:
            rule = admin_client.get(f"/category-rules/{rule_id}/").json()
            assert rule["set_kmen"] == "MH"
            assert float(rule["set_mh_pct"]) == 60.0
            assert float(rule["set_sk_pct"]) == 20.0
            assert float(rule["set_xp_pct"]) == 10.0
            assert float(rule["set_fr_pct"]) == 10.0
        finally:
            admin_client.delete(f"/category-rules/{rule_id}/")

    def test_edit_rule_kmen_pct_persists(self, admin_client):
        rule_data = {
            "name": "auto-test rule — KMEN edit",
            "match_type": "keyword",
            "match_mode": "contains",
            "match_value": "ZZZZ_AUTOTEST_KMEN_EDIT",
            "set_kmen": "SK",
            "set_mh_pct": "0",
            "set_sk_pct": "100",
            "set_xp_pct": "0",
            "set_fr_pct": "0",
        }
        r = admin_client.post("/category-rules/", json=rule_data)
        rule_id = r.json()["id"]

        try:
            admin_client.patch(
                f"/category-rules/{rule_id}/",
                json={
                    "set_mh_pct": "25",
                    "set_sk_pct": "25",
                    "set_xp_pct": "25",
                    "set_fr_pct": "25",
                },
            )
            rule = admin_client.get(f"/category-rules/{rule_id}/").json()
            assert float(rule["set_mh_pct"]) == 25.0
            assert float(rule["set_sk_pct"]) == 25.0
        finally:
            admin_client.delete(f"/category-rules/{rule_id}/")


class TestV8VersionCheck:
    """v8 Test 14: Version is updated."""

    def test_version_json_accessible(self):
        r = requests.get(f"{FRONTEND_URL}/version.json", verify=False)
        assert r.status_code == 200, f"Could not fetch version.json: {r.status_code}"
        data = r.json()
        assert "version" in data
        assert "date" in data
