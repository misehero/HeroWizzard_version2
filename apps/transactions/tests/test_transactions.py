"""
Mise HERo Finance - Transactions Tests
=======================================
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from apps.transactions.models import CategoryRule
from apps.transactions.services import TransactionImporter

from .factories import (AdminUserFactory, CategorizedTransactionFactory,
                        CategoryRuleFactory, ProjectFactory,
                        SplitTransactionFactory, TransactionFactory,
                        UserFactory)

# =============================================================================
# MODEL TESTS
# =============================================================================


@pytest.mark.django_db
class TestTransactionModel:
    """Tests for Transaction model."""

    def test_create_transaction(self):
        """Test basic transaction creation."""
        txn = TransactionFactory()
        assert txn.id is not None
        assert txn.datum is not None
        assert txn.castka != 0

    def test_prijem_vydaj_auto_set(self):
        """Test P/V is correctly set based on amount sign."""
        income = TransactionFactory(castka=Decimal("1000"))
        expense = TransactionFactory(castka=Decimal("-500"))

        assert income.prijem_vydaj == "P"
        assert expense.prijem_vydaj == "V"

    def test_kmen_split_validation_sum_100(self):
        """Test KMEN split must sum to 100."""
        txn = TransactionFactory.build(
            mh_pct=Decimal("30"),
            sk_pct=Decimal("30"),
            xp_pct=Decimal("30"),
            fr_pct=Decimal("10"),
        )
        # Should be valid (sum = 100)
        txn.full_clean()
        txn.save()

    def test_kmen_split_validation_sum_0(self):
        """Test KMEN split can be all zeros."""
        txn = TransactionFactory.build(
            mh_pct=Decimal("0"),
            sk_pct=Decimal("0"),
            xp_pct=Decimal("0"),
            fr_pct=Decimal("0"),
        )
        # Should be valid (sum = 0)
        txn.full_clean()
        txn.save()

    def test_kmen_split_validation_invalid_sum(self):
        """Test KMEN split fails if sum is not 0 or 100."""
        txn = TransactionFactory.build(
            mh_pct=Decimal("30"),
            sk_pct=Decimal("30"),
            xp_pct=Decimal("30"),
            fr_pct=Decimal("5"),  # Sum = 95
        )
        with pytest.raises(ValidationError):
            txn.full_clean()

    def test_is_categorized_property(self):
        """Test is_categorized property."""
        uncategorized = TransactionFactory(prijem_vydaj="", druh="")
        categorized = CategorizedTransactionFactory()

        assert not uncategorized.is_categorized
        assert categorized.is_categorized

    def test_kmen_split_assigned_property(self):
        """Test kmen_split_assigned property."""
        no_split = TransactionFactory()
        with_split = SplitTransactionFactory()

        assert not no_split.kmen_split_assigned
        assert with_split.kmen_split_assigned

    def test_unique_id_transakce_constraint(self):
        """Test duplicate bank transaction ID is rejected."""
        TransactionFactory(id_transakce="TXN123456")

        with pytest.raises(Exception):  # IntegrityError
            TransactionFactory(id_transakce="TXN123456")


@pytest.mark.django_db
class TestCategoryRuleModel:
    """Tests for CategoryRule model."""

    def test_create_rule(self):
        """Test basic rule creation."""
        rule = CategoryRuleFactory()
        assert rule.id is not None
        assert rule.is_active

    def test_regex_validation(self):
        """Test regex pattern validation."""
        # Valid regex
        rule = CategoryRuleFactory.build(
            match_mode="regex", match_value=r"\d{10}/\d{4}"
        )
        rule.full_clean()  # Should not raise

        # Invalid regex
        rule_invalid = CategoryRuleFactory.build(
            match_mode="regex", match_value=r"[invalid"
        )
        with pytest.raises(ValidationError):
            rule_invalid.full_clean()


# =============================================================================
# SERVICE TESTS
# =============================================================================


@pytest.mark.django_db
class TestTransactionImporter:
    """Tests for TransactionImporter service."""

    def test_parse_czech_decimal(self):
        """Test Czech decimal format parsing."""
        importer = TransactionImporter()

        assert importer._parse_decimal("1 234,56") == Decimal("1234.56")
        assert importer._parse_decimal("1234,56") == Decimal("1234.56")
        assert importer._parse_decimal("-500,00") == Decimal("-500.00")

    def test_parse_date_formats(self):
        """Test various date format parsing."""
        importer = TransactionImporter()

        assert importer._parse_date("15.03.2024") == date(2024, 3, 15)
        assert importer._parse_date("15/03/2024") == date(2024, 3, 15)
        assert importer._parse_date("2024-03-15") == date(2024, 3, 15)

    def test_rule_matching_exact(self):
        """Test exact match rule."""
        importer = TransactionImporter()

        rule = CategoryRuleFactory.build(
            match_mode="exact",
            match_value="123456789/0100",
            case_sensitive=False,
        )

        assert importer._rule_matches(rule, "123456789/0100")
        assert not importer._rule_matches(rule, "123456789/0200")

    def test_rule_matching_contains(self):
        """Test contains match rule."""
        importer = TransactionImporter()

        rule = CategoryRuleFactory.build(
            match_mode="contains",
            match_value="vodafone",
            case_sensitive=False,
        )

        assert importer._rule_matches(rule, "Platba VODAFONE CZ s.r.o.")
        assert importer._rule_matches(rule, "vodafone monthly")
        assert not importer._rule_matches(rule, "T-Mobile")

    def test_rule_matching_regex(self):
        """Test regex match rule."""
        importer = TransactionImporter()

        rule = CategoryRuleFactory.build(
            match_mode="regex",
            match_value=r"VS:\s*\d{10}",
            case_sensitive=False,
        )

        assert importer._rule_matches(rule, "Platba VS: 1234567890")
        assert importer._rule_matches(rule, "VS:1234567890 faktura")
        assert not importer._rule_matches(rule, "VS: 123")


# =============================================================================
# API TESTS
# =============================================================================


@pytest.mark.django_db
class TestTransactionAPI:
    """Tests for Transaction API endpoints."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def auth_client(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)
        return api_client

    @pytest.fixture
    def admin_client(self, api_client):
        admin = AdminUserFactory()
        api_client.force_authenticate(user=admin)
        return api_client

    def test_list_transactions_unauthenticated(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get("/api/v1/transactions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_transactions(self, auth_client):
        """Test listing transactions."""
        TransactionFactory.create_batch(5)

        response = auth_client.get("/api/v1/transactions/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 5

    def test_filter_by_date_range(self, auth_client):
        """Test filtering by date range."""
        TransactionFactory(datum=date(2024, 1, 15))
        TransactionFactory(datum=date(2024, 2, 15))
        TransactionFactory(datum=date(2024, 3, 15))

        response = auth_client.get(
            "/api/v1/transactions/",
            {"date_from": "2024-02-01", "date_to": "2024-02-28"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_filter_by_status(self, auth_client):
        """Test filtering by status."""
        TransactionFactory.create_batch(3, status="importovano")
        TransactionFactory.create_batch(2, status="zpracovano")

        response = auth_client.get("/api/v1/transactions/", {"status": "zpracovano"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_update_transaction(self, auth_client):
        """Test updating transaction app columns."""
        project = ProjectFactory()
        txn = TransactionFactory()

        response = auth_client.patch(
            f"/api/v1/transactions/{txn.id}/",
            {
                "status": "zpracovano",
                "druh": "Fixní",
                "projekt": project.id,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        txn.refresh_from_db()
        assert txn.status == "zpracovano"
        assert txn.druh == "Fixní"
        assert txn.projekt_id == project.id

    def test_bulk_update(self, auth_client):
        """Test bulk updating transactions."""
        txns = TransactionFactory.create_batch(5)
        ids = [str(t.id) for t in txns[:3]]

        response = auth_client.post(
            "/api/v1/transactions/bulk_update/",
            {
                "ids": ids,
                "status": "zpracovano",
                "druh": "Variabilní",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["updated_count"] == 3

    def test_stats_endpoint(self, auth_client):
        """Test statistics endpoint."""
        CategorizedTransactionFactory.create_batch(10)

        response = auth_client.get("/api/v1/transactions/stats/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_count" in response.data
        assert "total_income" in response.data
        assert "total_expense" in response.data


@pytest.mark.django_db
class TestCategoryRuleAPI:
    """Tests for CategoryRule API endpoints."""

    @pytest.fixture
    def auth_client(self):
        client = APIClient()
        user = UserFactory()
        client.force_authenticate(user=user)
        return client

    def test_list_rules(self, auth_client):
        """Test listing category rules."""
        CategoryRuleFactory.create_batch(5)

        response = auth_client.get("/api/v1/category-rules/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_create_rule(self, auth_client):
        """Test creating a category rule."""
        response = auth_client.post(
            "/api/v1/category-rules/",
            {
                "name": "Vodafone Rule",
                "match_type": "merchant",
                "match_mode": "contains",
                "match_value": "vodafone",
                "set_druh": "Fixní",
                "set_detail": "Telefon",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert CategoryRule.objects.filter(name="Vodafone Rule").exists()
