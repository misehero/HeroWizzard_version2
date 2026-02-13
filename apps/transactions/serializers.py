"""
Mise HERo Finance - Transactions Serializers
=============================================
DRF serializers for all transaction-related models.
"""

from decimal import Decimal

from django.db import transaction as db_transaction
from rest_framework import serializers

from .models import (CategoryRule, CostDetail, ImportBatch, Product,
                     ProductSubgroup, Project, Transaction,
                     TransactionAuditLog)

# =============================================================================
# LOOKUP SERIALIZERS
# =============================================================================


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project lookup model."""

    class Meta:
        model = Project
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ProductSubgroupSerializer(serializers.ModelSerializer):
    """Serializer for ProductSubgroup (nested in Product)."""

    class Meta:
        model = ProductSubgroup
        fields = ["id", "name", "description", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product lookup model."""

    subgroups = ProductSubgroupSerializer(many=True, read_only=True)
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_display",
            "description",
            "is_active",
            "subgroups",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProductSubgroupDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ProductSubgroup with product info."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_category = serializers.CharField(
        source="product.get_category_display", read_only=True
    )

    class Meta:
        model = ProductSubgroup
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "product",
            "product_name",
            "product_category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CostDetailSerializer(serializers.ModelSerializer):
    """Serializer for CostDetail lookup model."""

    druh_type_display = serializers.CharField(
        source="get_druh_type_display", read_only=True
    )

    class Meta:
        model = CostDetail
        fields = [
            "id",
            "druh_type",
            "druh_type_display",
            "druh_value",
            "detail",
            "is_active",
        ]


# =============================================================================
# TRANSACTION SERIALIZERS
# =============================================================================


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for transaction list views.
    Shows key fields for table display.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prijem_vydaj_display = serializers.CharField(
        source="get_prijem_vydaj_display", read_only=True
    )
    projekt_name = serializers.CharField(
        source="projekt.name", read_only=True, allow_null=True
    )
    produkt_name = serializers.CharField(
        source="produkt.name", read_only=True, allow_null=True
    )

    updated_by_email = serializers.EmailField(
        source="updated_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            # Primary key
            "id",
            # Key bank columns (visible)
            "datum",
            "ucet",
            "typ",
            "poznamka_zprava",
            "variabilni_symbol",
            "castka",
            # Counterparty (for table display)
            "nazev_protiuctu",
            "nazev_merchanta",
            # Key app columns
            "status",
            "status_display",
            "prijem_vydaj",
            "prijem_vydaj_display",
            "druh",
            "detail",
            "kmen",
            "projekt",
            "projekt_name",
            "produkt",
            "produkt_name",
            # Active flag
            "is_active",
            # Computed
            "is_categorized",
            # Audit
            "updated_at",
            "updated_by_email",
        ]


class TransactionAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for transaction audit log entries."""

    user_email = serializers.EmailField(
        source="user.email", read_only=True, allow_null=True
    )

    class Meta:
        model = TransactionAuditLog
        fields = ["id", "action", "details", "user_email", "created_at"]


class TransactionDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for transaction detail/edit views.
    Includes all 22 bank columns + 14 app columns.
    """

    # Display values for choices
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prijem_vydaj_display = serializers.CharField(
        source="get_prijem_vydaj_display", read_only=True
    )
    vlastni_nevlastni_display = serializers.CharField(
        source="get_vlastni_nevlastni_display", read_only=True
    )
    kmen_display = serializers.CharField(source="get_kmen_display", read_only=True)

    # Related object names
    projekt_name = serializers.CharField(
        source="projekt.name", read_only=True, allow_null=True
    )
    produkt_name = serializers.CharField(
        source="produkt.name", read_only=True, allow_null=True
    )
    podskupina_name = serializers.CharField(
        source="podskupina.name", read_only=True, allow_null=True
    )

    # Computed properties
    is_categorized = serializers.BooleanField(read_only=True)
    kmen_split_assigned = serializers.BooleanField(read_only=True)

    # Audit: updated_by
    updated_by_email = serializers.EmailField(
        source="updated_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            # Primary key
            "id",
            # === 22 BANK COLUMNS (read-only from CSV) ===
            # Visible (6)
            "datum",
            "ucet",
            "typ",
            "poznamka_zprava",
            "variabilni_symbol",
            "castka",
            # Hidden (16)
            "datum_zauctovani",
            "cislo_protiuctu",
            "nazev_protiuctu",
            "typ_transakce",
            "konstantni_symbol",
            "specificky_symbol",
            "puvodni_castka",
            "puvodni_mena",
            "poplatky",
            "id_transakce",
            "vlastni_poznamka",
            "nazev_merchanta",
            "mesto",
            "mena",
            "banka_protiuctu",
            "reference",
            # === 14 APP COLUMNS (editable) ===
            # Status
            "status",
            "status_display",
            # Basic categorization
            "prijem_vydaj",
            "prijem_vydaj_display",
            "vlastni_nevlastni",
            "vlastni_nevlastni_display",
            "dane",
            "druh",
            "detail",
            # KMEN split
            "kmen",
            "kmen_display",
            "mh_pct",
            "sk_pct",
            "xp_pct",
            "fr_pct",
            # Project/Product
            "projekt",
            "projekt_name",
            "produkt",
            "produkt_name",
            "podskupina",
            "podskupina_name",
            # === ACTIVE FLAG ===
            "is_active",
            # === COMPUTED ===
            "is_categorized",
            "kmen_split_assigned",
            # === AUDIT ===
            "import_batch_id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "updated_by_email",
        ]
        read_only_fields = [
            # Bank columns are never editable via API
            "datum",
            "ucet",
            "typ",
            "poznamka_zprava",
            "variabilni_symbol",
            "castka",
            "datum_zauctovani",
            "cislo_protiuctu",
            "nazev_protiuctu",
            "typ_transakce",
            "konstantni_symbol",
            "specificky_symbol",
            "puvodni_castka",
            "puvodni_mena",
            "poplatky",
            "id_transakce",
            "vlastni_poznamka",
            "nazev_merchanta",
            "mesto",
            "mena",
            "banka_protiuctu",
            "reference",
            # Audit fields
            "import_batch_id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate(self, data):
        """
        Validate KMEN percentage split sums to 100.
        """
        # Get current values or defaults
        instance = self.instance
        mh_pct = data.get(
            "mh_pct",
            getattr(instance, "mh_pct", Decimal("0")) if instance else Decimal("0"),
        )
        sk_pct = data.get(
            "sk_pct",
            getattr(instance, "sk_pct", Decimal("0")) if instance else Decimal("0"),
        )
        xp_pct = data.get(
            "xp_pct",
            getattr(instance, "xp_pct", Decimal("0")) if instance else Decimal("0"),
        )
        fr_pct = data.get(
            "fr_pct",
            getattr(instance, "fr_pct", Decimal("0")) if instance else Decimal("0"),
        )

        total = (
            (mh_pct or Decimal("0"))
            + (sk_pct or Decimal("0"))
            + (xp_pct or Decimal("0"))
            + (fr_pct or Decimal("0"))
        )

        if total != Decimal("0") and total != Decimal("100"):
            raise serializers.ValidationError(
                {
                    "mh_pct": f"KMEN % součet musí být 0 nebo 100. Aktuální součet: {total}%"
                }
            )

        # Validate podskupina belongs to produkt
        podskupina = data.get("podskupina")
        produkt = data.get(
            "produkt", getattr(instance, "produkt", None) if instance else None
        )

        if podskupina and produkt and podskupina.product_id != produkt.pk:
            raise serializers.ValidationError(
                {"podskupina": "Vybraná podskupina nepatří k vybranému produktu."}
            )

        return data


class ManualTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for manually created transactions.
    Allows writing key bank fields (datum, castka, …) that are read-only
    on TransactionDetailSerializer, plus all app-column fields.

    The six bank fields below are declared explicitly because the model
    marks them ``editable=False``.  Without explicit declarations DRF's
    ModelSerializer would silently treat them as read_only and drop them
    from ``validated_data``.
    """

    # -- bank fields that must be writable for manual entry --
    datum = serializers.DateField()
    castka = serializers.DecimalField(max_digits=15, decimal_places=2)
    poznamka_zprava = serializers.CharField(
        required=False, allow_blank=True, default="", style={"base_template": "textarea.html"}
    )
    nazev_protiuctu = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )
    variabilni_symbol = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=20
    )
    typ = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=100
    )

    class Meta:
        model = Transaction
        fields = [
            # Key bank fields — writable for manual entry
            "datum",
            "castka",
            "poznamka_zprava",
            "nazev_protiuctu",
            "variabilni_symbol",
            "typ",
            # App fields
            "prijem_vydaj",
            "vlastni_nevlastni",
            "dane",
            "druh",
            "detail",
            "kmen",
            "mh_pct",
            "sk_pct",
            "xp_pct",
            "fr_pct",
            "projekt",
            "produkt",
            "podskupina",
        ]

    def validate(self, data):
        """Reuse KMEN % and podskupina validation from detail serializer."""
        mh = data.get("mh_pct", Decimal("0")) or Decimal("0")
        sk = data.get("sk_pct", Decimal("0")) or Decimal("0")
        xp = data.get("xp_pct", Decimal("0")) or Decimal("0")
        fr = data.get("fr_pct", Decimal("0")) or Decimal("0")
        total = mh + sk + xp + fr

        if total != Decimal("0") and total != Decimal("100"):
            raise serializers.ValidationError(
                {"mh_pct": f"KMEN % součet musí být 0 nebo 100. Aktuální součet: {total}%"}
            )

        podskupina = data.get("podskupina")
        produkt = data.get("produkt")
        if podskupina and produkt and podskupina.product_id != produkt.pk:
            raise serializers.ValidationError(
                {"podskupina": "Vybraná podskupina nepatří k vybranému produktu."}
            )

        return data


class TransactionBulkUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk updating multiple transactions.
    Only includes app columns that can be bulk-edited.
    """

    ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        help_text="List of transaction IDs to update",
    )

    # Fields that can be bulk updated
    status = serializers.ChoiceField(choices=Transaction.Status.choices, required=False)
    prijem_vydaj = serializers.ChoiceField(
        choices=Transaction.PrijemVydaj.choices, required=False
    )
    vlastni_nevlastni = serializers.ChoiceField(
        choices=Transaction.VlastniNevlastni.choices, required=False
    )
    dane = serializers.BooleanField(required=False, allow_null=True)
    druh = serializers.CharField(max_length=50, required=False, allow_blank=True)
    detail = serializers.CharField(max_length=200, required=False, allow_blank=True)
    kmen = serializers.ChoiceField(
        choices=Transaction.Kmen.choices, required=False, allow_blank=True
    )
    mh_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    sk_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    xp_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    fr_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    projekt = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.filter(is_active=True), required=False, allow_null=True
    )
    produkt = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True), required=False, allow_null=True
    )
    podskupina = serializers.PrimaryKeyRelatedField(
        queryset=ProductSubgroup.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    def validate(self, data):
        """Validate KMEN split if any percentage fields are provided."""
        pct_fields = ["mh_pct", "sk_pct", "xp_pct", "fr_pct"]
        provided_pcts = {
            k: v for k, v in data.items() if k in pct_fields and v is not None
        }

        if provided_pcts:
            # If any percentage is provided, all must be provided
            if len(provided_pcts) != 4:
                raise serializers.ValidationError(
                    "Při úpravě KMEN % musí být zadány všechny 4 hodnoty (MH%, ŠK%, XP%, FR%)."
                )

            total = sum(provided_pcts.values())
            if total != Decimal("0") and total != Decimal("100"):
                raise serializers.ValidationError(
                    {
                        "mh_pct": f"KMEN % součet musí být 0 nebo 100. Aktuální součet: {total}%"
                    }
                )

        return data

    def update(self, validated_data):
        """Perform bulk update and return count of updated records."""
        ids = validated_data.pop("ids")

        # Remove None values - we only update explicitly provided fields
        update_data = {k: v for k, v in validated_data.items() if v is not None}

        if not update_data:
            return 0

        with db_transaction.atomic():
            count = Transaction.objects.filter(id__in=ids).update(**update_data)

        return count


# =============================================================================
# CATEGORY RULE SERIALIZERS
# =============================================================================


class CategoryRuleSerializer(serializers.ModelSerializer):
    """Serializer for CategoryRule model."""

    match_type_display = serializers.CharField(
        source="get_match_type_display", read_only=True
    )
    match_mode_display = serializers.CharField(
        source="get_match_mode_display", read_only=True
    )
    created_by_email = serializers.EmailField(
        source="created_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = CategoryRule
        fields = [
            "id",
            "name",
            "description",
            # Matching
            "match_type",
            "match_type_display",
            "match_mode",
            "match_mode_display",
            "match_value",
            "case_sensitive",
            "priority",
            # Settings to apply
            "set_prijem_vydaj",
            "set_vlastni_nevlastni",
            "set_dane",
            "set_druh",
            "set_detail",
            "set_kmen",
            "set_mh_pct",
            "set_sk_pct",
            "set_xp_pct",
            "set_fr_pct",
            "set_projekt",
            "set_produkt",
            "set_podskupina",
            # Audit
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_email",
        ]
        read_only_fields = ["created_at", "updated_at", "created_by"]

    def validate_match_value(self, value):
        """Validate regex pattern if match_mode is regex."""
        # Get match_mode from initial_data since it might not be validated yet
        match_mode = self.initial_data.get("match_mode", "exact")

        if match_mode == CategoryRule.MatchMode.REGEX:
            import re

            try:
                re.compile(value)
            except re.error as e:
                raise serializers.ValidationError(f"Neplatný regex vzor: {e}")

        return value

    def create(self, validated_data):
        """Set created_by from request user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


# =============================================================================
# IMPORT BATCH SERIALIZERS
# =============================================================================


class ImportBatchSerializer(serializers.ModelSerializer):
    """Serializer for ImportBatch model."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_email = serializers.EmailField(
        source="created_by.email", read_only=True, allow_null=True
    )
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "filename",
            "status",
            "status_display",
            "total_rows",
            "imported_count",
            "skipped_count",
            "error_count",
            "error_details",
            "started_at",
            "completed_at",
            "duration_seconds",
            "created_at",
            "created_by",
            "created_by_email",
        ]
        read_only_fields = fields  # All fields are read-only

    def get_duration_seconds(self, obj):
        """Calculate import duration in seconds."""
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class CSVUploadSerializer(serializers.Serializer):
    """Serializer for CSV file upload."""

    file = serializers.FileField(
        help_text="CSV file to import (semicolon-delimited, UTF-8 with BOM)"
    )

    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file extension
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Soubor musí mít příponu .csv")

        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Soubor je příliš velký. Maximum je {max_size // (1024*1024)}MB."
            )

        return value


# =============================================================================
# STATISTICS / AGGREGATION SERIALIZERS
# =============================================================================


class TransactionStatsSerializer(serializers.Serializer):
    """Serializer for transaction statistics."""

    total_count = serializers.IntegerField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=15, decimal_places=2)

    by_status = serializers.DictField(child=serializers.IntegerField())
    by_kmen = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2)
    )
    by_druh = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2)
    )

    uncategorized_count = serializers.IntegerField()
    uncategorized_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class MonthlyTrendSerializer(serializers.Serializer):
    """Serializer for monthly trend data."""

    month = serializers.DateField()
    income = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    net = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()
