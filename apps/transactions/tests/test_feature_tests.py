"""
Mise HERo Finance - Feature Tests
==================================
Comprehensive tests for:
1. Creditas CSV Import
2. Raiffeisen CSV Import
3. Transaction Editing
4. Manual Transaction Creation
5. Category Rule CRUD
6. Category Rules Applied During Import (Integration)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.transactions.models import CategoryRule, ImportBatch, Transaction
from apps.transactions.tests.factories import (
    CategoryRuleFactory,
    ProductFactory,
    ProductSubgroupFactory,
    ProjectFactory,
    TransactionFactory,
)

# =============================================================================
# CSV CONTENT CONSTANTS
# =============================================================================

# Exact copy of docs/test_creditas.csv (5 transaction rows)
CREDITAS_CSV_CONTENT = (
    "Typ \u00fa\u010dtu;IBAN;BIC;Vlastn\u00edk \u00fa\u010dtu;\u010c\u00edslo \u00fa\u010dtu\r\n"
    "B\u011b\u017en\u00fd \u00fa\u010det;CZ1234567890123456789012;FIOBCZPP;Test Company s.r.o.;118514285/2250\r\n"
    "\r\n"
    "M\u016fj \u00fa\u010det;M\u016fj \u00fa\u010det-banka;N\u00e1zev m\u00e9ho \u00fa\u010dtu;"
    "Datum za\u00fa\u010dtov\u00e1n\u00ed;Datum proveden\u00ed;"
    "Proti\u00fa\u010det;Proti\u00fa\u010det-banka;N\u00e1zev proti\u00fa\u010dtu;"
    "K\u00f3d transakce;VS;SS;KS;E2E;"
    "Zpr\u00e1va pro protistranu;Pozn\u00e1mka;Platba/Vklad;"
    "\u010c\u00e1stka;M\u011bna;Kategorie\r\n"
    "118514285;2250;Hlavn\u00ed \u00fa\u010det;15.01.2025;;987654321;1234;"
    "Dodavatel a.s.;\u00dahrada;10001;;;REF-CR-001;"
    "\u00dahrada faktury FV-2025-001;P\u0159ijat\u00e9 platby;Vklad;"
    "15 000,00;CZK;P\u0159\u00edchod\r\n"
    "118514285;2250;Hlavn\u00ed \u00fa\u010det;16.01.2025;;111222333;5678;"
    "Konzultant spol. s r.o.;Platba;10002;;;REF-CR-002;"
    "Platba za konzulta\u010dn\u00ed slu\u017eby;;Platba;"
    "-3 750,50;CZK;Odchod\r\n"
    "118514285;2250;Hlavn\u00ed \u00fa\u010det;17.01.2025;;444555666;9012;"
    "Obchodn\u00ed partner v.o.s.;\u00dahrada;10003;100;;REF-CR-003;"
    "N\u00e1kup kancel\u00e1\u0159\u00edho materi\u00e1lu;;Platba;"
    "-890,00;CZK;Odchod\r\n"
    "118514285;2250;Hlavn\u00ed \u00fa\u010det;20.01.2025;;789101112;2250;"
    "Nov\u00e1k Jan;Platba;;;;REF-CR-004;"
    "V\u00fdplata mzdy prosinec 2024;;Platba;"
    "-45 200,00;CZK;Odchod\r\n"
    "118514285;2250;Hlavn\u00ed \u00fa\u010det;22.01.2025;;333444555;1234;"
    "Poji\u0161\u0165ovna Czech a.s.;\u00dahrada;10005;;;REF-CR-005;"
    "Pojistn\u00e9 firemn\u00ed automobil;;Platba;"
    "-2 100,00;CZK;Odchod\r\n"
)

# Exact copy of docs/test_raiffeisen.csv (5 transaction rows)
RAIFFEISEN_CSV_CONTENT = (
    "Datum proveden\u00ed;Datum za\u00fa\u010dtov\u00e1n\u00ed;"
    "\u010c\u00edslo \u00fa\u010dtu;N\u00e1zev \u00fa\u010dtu;"
    "Kategorie transakce;\u010c\u00edslo proti\u00fa\u010dtu;"
    "N\u00e1zev proti\u00fa\u010dtu;Typ transakce;Zpr\u00e1va;"
    "Pozn\u00e1mka;VS;KS;SS;Za\u00fa\u010dtovan\u00e1 \u010d\u00e1stka;"
    "M\u011bna \u00fa\u010dtu;P\u016fvodn\u00ed \u010d\u00e1stka a m\u011bna;"
    "P\u016fvodn\u00ed \u010d\u00e1stka a m\u011bna;Poplatek;"
    "Id transakce;Vlastn\u00ed pozn\u00e1mka;"
    "N\u00e1zev obchodn\u00edka;M\u011bsto\r\n"
    "15.01.2025 10:30;15.01.2025;1234567890/2200;Hlavn\u00ed \u00fa\u010det;"
    "P\u0159\u00edchod;987654321/1234;Klient Alpha s.r.o.;"
    "P\u0159\u00edchod na \u00fa\u010det;\u00dahrada za zak\u00e1zku CZ-2025-001;;"
    "20250101;;;22 500,00;CZK;22 500,00;CZK;;RB-TEST-001;;"
    "Klient Alpha s.r.o.;Praha\r\n"
    "16.01.2025 08:15;16.01.2025;1234567890/2200;Hlavn\u00ed \u00fa\u010det;"
    "N\u00e1kup;;;\u00dahrada kartou;N\u00e1kup potravin ve Westernmarket;;;;;"
    "-1 234,50;CZK;1 234,50;CZK;;RB-TEST-002;;"
    "Westernmarket s.r.o.;Brno\r\n"
    "17.01.2025 09:00;17.01.2025;1234567890/2200;Hlavn\u00ed \u00fa\u010det;"
    "Platba;555666777/3300;Pron\u00e1jem a.s.;"
    "Platba na \u00fa\u010det;N\u00e1jemn\u00e9 leden 2025;;"
    "20250103;200;;-18 000,00;CZK;18 000,00;CZK;0,00;RB-TEST-003;;;"
    "Praha\r\n"
    "20.01.2025 06:30;20.01.2025;1234567890/2200;Hlavn\u00ed \u00fa\u010det;"
    "Platba;888999111/2100;\u010cEZ Group a.s.;"
    "Platba na \u00fa\u010det;Elekt\u0159ina leden 2025;;"
    "20250104;;;-3 456,78;CZK;3 456,78;CZK;;RB-TEST-004;;"
    "\u010cEZ Group;\u010cesk\u00e9 Bud\u011bjovice\r\n"
    "22.01.2025 14:00;22.01.2025;1234567890/2200;Hlavn\u00ed \u00fa\u010det;"
    "P\u0159evod;123456789/6800;Vlastn\u00ed \u00fa\u010det \u0160patn\u00fd;"
    "P\u0159evod mezi \u00fa\u010dty;;;;;;10 000,00;CZK;10 000,00;CZK;;"
    "RB-TEST-005;P\u0159evod ze spo\u0159ic\u00edho \u00fa\u010dtu;;\r\n"
)


# =============================================================================
# HELPERS
# =============================================================================


def make_csv_upload(content: str, filename: str = "test.csv") -> SimpleUploadedFile:
    """Create a SimpleUploadedFile from CSV string content."""
    return SimpleUploadedFile(
        name=filename,
        content=content.encode("utf-8-sig"),
        content_type="text/csv",
    )


# =============================================================================
# TEST CLASS 1: CREDITAS CSV IMPORT
# =============================================================================


@pytest.mark.django_db
class TestCreditasCSVImport:
    """Tests for Creditas bank CSV import via /api/v1/imports/upload/."""

    def test_creditas_import_success(self, authenticated_client):
        """Upload 5-row Creditas CSV -> 201, imported=5."""
        response = authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(CREDITAS_CSV_CONTENT, "creditas_test.csv")},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["total_rows"] == 5
        assert data["imported"] == 5
        assert data["errors"] == 0

    def test_creditas_field_mapping(self, authenticated_client):
        """Verify Creditas field mapping: account joining, datum fallback."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(CREDITAS_CSV_CONTENT, "creditas_test.csv")},
            format="multipart",
        )
        # Get first transaction (highest positive amount)
        txn = Transaction.objects.filter(castka=Decimal("15000.00")).first()
        assert txn is not None
        assert txn.ucet == "118514285/2250"
        assert txn.cislo_protiuctu == "987654321/1234"
        assert txn.banka_protiuctu == "1234"
        assert txn.datum == date(2025, 1, 15)  # Fallback from datum_zauctovani
        assert txn.variabilni_symbol == "10001"
        assert txn.reference == "REF-CR-001"
        assert "\u00dahrada faktury FV-2025-001" in txn.poznamka_zprava

    def test_creditas_negative_amounts_auto_pv(self, authenticated_client):
        """Negative amounts get P/V='V', positive get 'P'."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(CREDITAS_CSV_CONTENT, "creditas_test.csv")},
            format="multipart",
        )
        positive_txn = Transaction.objects.filter(castka__gt=0).first()
        assert positive_txn.prijem_vydaj == "P"

        negative_txn = Transaction.objects.filter(castka__lt=0).first()
        assert negative_txn.prijem_vydaj == "V"

    def test_creditas_creates_batch(self, authenticated_client):
        """ImportBatch record created with status='completed'."""
        response = authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(CREDITAS_CSV_CONTENT, "creditas_test.csv")},
            format="multipart",
        )
        batch_id = response.json()["batch_id"]
        batch = ImportBatch.objects.get(id=batch_id)
        assert batch.status == "completed"
        assert batch.imported_count == 5
        assert batch.filename == "creditas_test.csv"


# =============================================================================
# TEST CLASS 2: RAIFFEISEN CSV IMPORT
# =============================================================================


@pytest.mark.django_db
class TestRaiffeisenCSVImport:
    """Tests for Raiffeisen bank CSV import via /api/v1/imports/upload/."""

    def test_raiffeisen_import_success(self, authenticated_client):
        """Upload 5-row Raiffeisen CSV -> 201, imported=5."""
        response = authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiffeisen_test.csv")},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["total_rows"] == 5
        assert data["imported"] == 5
        assert data["errors"] == 0

    def test_raiffeisen_field_mapping(self, authenticated_client):
        """Verify datetime parsing, id_transakce, merchant name."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiffeisen_test.csv")},
            format="multipart",
        )
        txn = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn.datum == date(2025, 1, 15)
        assert txn.ucet == "1234567890/2200"
        assert txn.castka == Decimal("22500.00")
        assert txn.nazev_merchanta == "Klient Alpha s.r.o."
        assert txn.mesto == "Praha"
        assert txn.cislo_protiuctu == "987654321/1234"

    def test_raiffeisen_duplicate_detection(self, authenticated_client):
        """Second import of same file: imported=0, skipped=5."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff1.csv")},
            format="multipart",
        )
        assert Transaction.objects.count() == 5

        response = authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff2.csv")},
            format="multipart",
        )
        data = response.json()
        assert data["imported"] == 0
        assert data["skipped"] == 5
        assert Transaction.objects.count() == 5  # No new transactions

    def test_raiffeisen_auto_prijem_vydaj(self, authenticated_client):
        """Positive amounts get P, negative get V."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiffeisen_test.csv")},
            format="multipart",
        )
        # RB-TEST-001: 22500 (positive)
        txn1 = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn1.prijem_vydaj == "P"

        # RB-TEST-002: -1234.50 (negative)
        txn2 = Transaction.objects.get(id_transakce="RB-TEST-002")
        assert txn2.prijem_vydaj == "V"

    def test_raiffeisen_czech_decimal(self, authenticated_client):
        """Czech decimal format '22 500,00' parsed to Decimal('22500.00')."""
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiffeisen_test.csv")},
            format="multipart",
        )
        txn = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn.castka == Decimal("22500.00")

        txn2 = Transaction.objects.get(id_transakce="RB-TEST-002")
        assert txn2.castka == Decimal("-1234.50")


# =============================================================================
# TEST CLASS 3: TRANSACTION EDITING
# =============================================================================


@pytest.mark.django_db
class TestTransactionEditing:
    """Tests for PATCH /api/v1/transactions/{id}/."""

    def test_update_status(self, authenticated_client):
        """PATCH status -> persisted."""
        txn = TransactionFactory()
        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {"status": "zpracovano"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        txn.refresh_from_db()
        assert txn.status == "zpracovano"

    def test_update_categorization(self, authenticated_client):
        """PATCH druh + detail + vlastni_nevlastni -> all saved."""
        txn = TransactionFactory(castka=Decimal("-1000"))
        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {
                "druh": "Fixn\u00ed",
                "detail": "N\u00e1jem kancel\u00e1\u0159e",
                "vlastni_nevlastni": "N",
                "prijem_vydaj": "V",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        txn.refresh_from_db()
        assert txn.druh == "Fixn\u00ed"
        assert txn.detail == "N\u00e1jem kancel\u00e1\u0159e"
        assert txn.vlastni_nevlastni == "N"

    def test_update_kmen_split_valid(self, authenticated_client):
        """PATCH KMEN 100/0/0/0 -> persisted."""
        txn = TransactionFactory()
        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {
                "kmen": "MH",
                "mh_pct": "100",
                "sk_pct": "0",
                "xp_pct": "0",
                "fr_pct": "0",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        txn.refresh_from_db()
        assert txn.kmen == "MH"
        assert txn.mh_pct == Decimal("100")

    def test_update_kmen_split_invalid(self, authenticated_client):
        """PATCH KMEN 50/10/0/0 (sum=60) -> 400."""
        txn = TransactionFactory()
        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {
                "mh_pct": "50",
                "sk_pct": "10",
                "xp_pct": "0",
                "fr_pct": "0",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_projekt_produkt(self, authenticated_client):
        """PATCH with FK IDs -> persisted."""
        txn = TransactionFactory()
        project = ProjectFactory()
        product = ProductFactory()
        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {"projekt": project.id, "produkt": product.id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        txn.refresh_from_db()
        assert txn.projekt_id == project.id
        assert txn.produkt_id == product.id

    def test_bank_fields_readonly(self, authenticated_client):
        """PATCH with bank fields -> silently ignored."""
        txn = TransactionFactory(castka=Decimal("5000"), datum=date(2025, 1, 1))
        original_castka = txn.castka
        original_datum = txn.datum

        response = authenticated_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {"castka": "999.99", "datum": "2020-06-15"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        txn.refresh_from_db()
        assert txn.castka == original_castka
        assert txn.datum == original_datum


# =============================================================================
# TEST CLASS 4: MANUAL TRANSACTION CREATION
# =============================================================================


@pytest.mark.django_db
class TestManualTransactionCreation:
    """Tests for POST /api/v1/transactions/create-manual/."""

    def test_create_minimal(self, authenticated_client):
        """POST datum + castka -> 201, status=upraveno, auto P/V."""
        response = authenticated_client.post(
            "/api/v1/transactions/create-manual/",
            {"datum": "2025-06-15", "castka": "5000.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "upraveno"
        assert data["mena"] == "CZK"
        assert data["prijem_vydaj"] == "P"  # Auto-set from positive amount

    def test_create_full(self, authenticated_client):
        """POST all fields -> all persisted."""
        project = ProjectFactory()
        product = ProductFactory()
        response = authenticated_client.post(
            "/api/v1/transactions/create-manual/",
            {
                "datum": "2025-06-15",
                "castka": "-10000.00",
                "poznamka_zprava": "Test transakce",
                "nazev_protiuctu": "Test partner",
                "variabilni_symbol": "12345",
                "typ": "Platba",
                "prijem_vydaj": "V",
                "vlastni_nevlastni": "V",
                "dane": True,
                "druh": "Fixn\u00ed",
                "detail": "Test detail",
                "kmen": "SK",
                "mh_pct": "0",
                "sk_pct": "100",
                "xp_pct": "0",
                "fr_pct": "0",
                "projekt": project.id,
                "produkt": product.id,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["druh"] == "Fixn\u00ed"
        assert data["kmen"] == "SK"
        assert data["dane"] is True
        assert data["projekt"] == project.id

    def test_create_negative_auto_vydaj(self, authenticated_client):
        """Negative amount -> prijem_vydaj='V' auto-set."""
        response = authenticated_client.post(
            "/api/v1/transactions/create-manual/",
            {"datum": "2025-06-15", "castka": "-2500.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["prijem_vydaj"] == "V"

    def test_create_missing_required(self, authenticated_client):
        """No datum -> 400."""
        response = authenticated_client.post(
            "/api/v1/transactions/create-manual/",
            {"castka": "5000.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_kmen(self, authenticated_client):
        """KMEN sum=60 -> 400."""
        response = authenticated_client.post(
            "/api/v1/transactions/create-manual/",
            {
                "datum": "2025-06-15",
                "castka": "5000.00",
                "mh_pct": "50",
                "sk_pct": "10",
                "xp_pct": "0",
                "fr_pct": "0",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# TEST CLASS 5: CATEGORY RULE CRUD
# =============================================================================


@pytest.mark.django_db
class TestCategoryRuleCRUD:
    """Tests for /api/v1/category-rules/ CRUD endpoints."""

    def test_create_protiucet_rule(self, authenticated_client, user):
        """POST protiucet/exact -> 201."""
        response = authenticated_client.post(
            "/api/v1/category-rules/",
            {
                "name": "Test Protiucet Rule",
                "match_type": "protiucet",
                "match_mode": "exact",
                "match_value": "123456789/0100",
                "set_druh": "Fixn\u00ed",
                "set_detail": "N\u00e1jem",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        rule = CategoryRule.objects.get(name="Test Protiucet Rule")
        assert rule.match_type == "protiucet"
        assert rule.match_mode == "exact"
        assert rule.set_druh == "Fixn\u00ed"
        assert rule.created_by == user

    def test_create_keyword_regex_rule(self, authenticated_client):
        """POST keyword/regex -> 201."""
        response = authenticated_client.post(
            "/api/v1/category-rules/",
            {
                "name": "Regex Rule",
                "match_type": "keyword",
                "match_mode": "regex",
                "match_value": r"FAKTURA\s*\d+",
                "set_prijem_vydaj": "V",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_invalid_regex(self, authenticated_client):
        """POST with bad regex -> 400."""
        response = authenticated_client.post(
            "/api/v1/category-rules/",
            {
                "name": "Bad Regex",
                "match_type": "keyword",
                "match_mode": "regex",
                "match_value": "[invalid",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_rule(self, authenticated_client, user):
        """PATCH name + set_druh -> updated."""
        rule = CategoryRuleFactory(created_by=user)
        response = authenticated_client.patch(
            f"/api/v1/category-rules/{rule.id}/",
            {"name": "Updated Rule", "set_druh": "Variabiln\u00ed"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        rule.refresh_from_db()
        assert rule.name == "Updated Rule"
        assert rule.set_druh == "Variabiln\u00ed"

    def test_delete_rule(self, authenticated_client, user):
        """DELETE -> 204."""
        rule = CategoryRuleFactory(created_by=user)
        response = authenticated_client.delete(
            f"/api/v1/category-rules/{rule.id}/",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CategoryRule.objects.filter(id=rule.id).exists()


# =============================================================================
# TEST CLASS 6: CATEGORY RULES APPLIED DURING IMPORT (INTEGRATION)
# =============================================================================


@pytest.mark.django_db
class TestCategoryRulesAppliedDuringImport:
    """Integration tests: rules applied to transactions during CSV import."""

    def test_protiucet_rule_during_import(self, authenticated_client, user):
        """Protiucet rule matches row 1 of Raiffeisen CSV."""
        CategoryRule.objects.create(
            name="Account Rule",
            match_type="protiucet",
            match_mode="exact",
            match_value="987654321/1234",
            set_druh="Projekt EU",
            set_detail="Klient Alpha",
            set_kmen="MH",
            set_mh_pct=Decimal("100"),
            set_sk_pct=Decimal("0"),
            set_xp_pct=Decimal("0"),
            set_fr_pct=Decimal("0"),
            created_by=user,
        )
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff.csv")},
            format="multipart",
        )
        # Row 1: cislo_protiuctu=987654321/1234 -> should match
        txn = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn.druh == "Projekt EU"
        assert txn.detail == "Klient Alpha"
        assert txn.kmen == "MH"
        assert txn.mh_pct == Decimal("100")

        # Row 2: no protiucet -> should NOT match
        txn2 = Transaction.objects.get(id_transakce="RB-TEST-002")
        assert txn2.druh == ""

    def test_merchant_rule_during_import(self, authenticated_client, user):
        """Merchant rule matches row 2 of Raiffeisen CSV."""
        CategoryRule.objects.create(
            name="Merchant Rule",
            match_type="merchant",
            match_mode="contains",
            match_value="Westernmarket",
            set_druh="Variabiln\u00ed",
            set_vlastni_nevlastni="V",
            created_by=user,
        )
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff.csv")},
            format="multipart",
        )
        txn = Transaction.objects.get(id_transakce="RB-TEST-002")
        assert txn.druh == "Variabiln\u00ed"
        assert txn.vlastni_nevlastni == "V"

    def test_keyword_rule_during_import(self, authenticated_client, user):
        """Keyword rule matches row 3 of Raiffeisen CSV (poznamka_zprava)."""
        CategoryRule.objects.create(
            name="Keyword Rule",
            match_type="keyword",
            match_mode="contains",
            match_value="N\u00e1jemn\u00e9",
            set_druh="Fixn\u00ed",
            set_detail="N\u00e1jem",
            created_by=user,
        )
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff.csv")},
            format="multipart",
        )
        txn = Transaction.objects.get(id_transakce="RB-TEST-003")
        assert txn.druh == "Fixn\u00ed"
        assert txn.detail == "N\u00e1jem"

    def test_rule_hierarchy_protiucet_over_merchant(self, authenticated_client, user):
        """Protiucet rule wins over merchant rule when both match."""
        CategoryRule.objects.create(
            name="Account Match",
            match_type="protiucet",
            match_mode="exact",
            match_value="987654321/1234",
            set_druh="ByAccount",
            created_by=user,
        )
        CategoryRule.objects.create(
            name="Merchant Match",
            match_type="merchant",
            match_mode="contains",
            match_value="Klient Alpha",
            set_druh="ByMerchant",
            created_by=user,
        )
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff.csv")},
            format="multipart",
        )
        # Row 1 matches both rules -> protiucet should win
        txn = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn.druh == "ByAccount"

    def test_inactive_rule_not_applied(self, authenticated_client, user):
        """Inactive rules should not be applied during import."""
        CategoryRule.objects.create(
            name="Inactive Rule",
            match_type="protiucet",
            match_mode="exact",
            match_value="987654321/1234",
            set_druh="ShouldNotAppear",
            is_active=False,
            created_by=user,
        )
        authenticated_client.post(
            "/api/v1/imports/upload/",
            {"file": make_csv_upload(RAIFFEISEN_CSV_CONTENT, "raiff.csv")},
            format="multipart",
        )
        txn = Transaction.objects.get(id_transakce="RB-TEST-001")
        assert txn.druh == ""  # Rule was inactive, so druh stays empty
