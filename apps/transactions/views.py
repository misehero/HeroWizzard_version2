"""
Mise HERo Finance - Transactions ViewSets
==========================================
DRF ViewSets for all transaction-related API endpoints.
"""

from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import TransactionFilter
from .models import (CategoryRule, CostDetail, ImportBatch, Product,
                     ProductSubgroup, Project, Transaction)
from .serializers import (CategoryRuleSerializer, CostDetailSerializer,
                          CSVUploadSerializer, ImportBatchSerializer,
                          MonthlyTrendSerializer, ProductSerializer,
                          ProductSubgroupDetailSerializer, ProjectSerializer,
                          TransactionBulkUpdateSerializer,
                          TransactionDetailSerializer,
                          TransactionListSerializer,
                          TransactionStatsSerializer)
from .services import TransactionImporter

# =============================================================================
# LOOKUP VIEWSETS
# =============================================================================


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Project lookup management.

    list: Get all projects
    retrieve: Get single project by ID
    create: Create new project (admin only)
    update: Update project (admin only)
    delete: Soft-delete project (admin only)
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        """Filter to active projects unless ?include_inactive=true."""
        qs = super().get_queryset()
        if not self.request.query_params.get("include_inactive"):
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        """Soft delete by setting is_active=False."""
        instance.is_active = False
        instance.save()


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Product lookup management.
    Includes nested subgroups in response.
    """

    queryset = Product.objects.prefetch_related("subgroups")
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["category", "name", "created_at"]
    ordering = ["category", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.query_params.get("include_inactive"):
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class ProductSubgroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for ProductSubgroup lookup management.
    """

    queryset = ProductSubgroup.objects.select_related("product")
    serializer_class = ProductSubgroupDetailSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["product", "is_active"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.query_params.get("include_inactive"):
            qs = qs.filter(is_active=True)
        return qs


class CostDetailViewSet(viewsets.ModelViewSet):
    """
    API endpoint for CostDetail (Druh/Detail) lookup management.
    """

    queryset = CostDetail.objects.all()
    serializer_class = CostDetailSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["druh_type", "is_active"]
    search_fields = ["druh_value", "detail"]


# =============================================================================
# TRANSACTION VIEWSET
# =============================================================================


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Transaction management.

    list: Get paginated transactions with filters
    retrieve: Get single transaction with full details
    update: Update app columns (bank columns are read-only)
    bulk_update: Update multiple transactions at once
    stats: Get aggregated statistics
    trends: Get monthly trend data
    """

    queryset = Transaction.objects.select_related(
        "projekt", "produkt", "podskupina", "import_batch"
    ).order_by("-datum", "-created_at")
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TransactionFilter
    search_fields = [
        "poznamka_zprava",
        "nazev_protiuctu",
        "nazev_merchanta",
        "variabilni_symbol",
        "vlastni_poznamka",
    ]
    ordering_fields = [
        "datum",
        "castka",
        "status",
        "prijem_vydaj",
        "druh",
        "created_at",
    ]
    ordering = ["-datum", "-created_at"]

    def get_serializer_class(self):
        """Use list serializer for list action, detail for others."""
        if self.action == "list":
            return TransactionListSerializer
        return TransactionDetailSerializer

    def get_queryset(self):
        """Apply date range filters from query params."""
        qs = super().get_queryset()

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            qs = qs.filter(datum__gte=date_from)
        if date_to:
            qs = qs.filter(datum__lte=date_to)

        return qs

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """
        Bulk update multiple transactions.

        POST /api/v1/transactions/bulk_update/
        {
            "ids": ["uuid1", "uuid2", ...],
            "status": "zpracovano",
            "projekt": "4cfuture"
        }
        """
        serializer = TransactionBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = serializer.update(serializer.validated_data)

        return Response(
            {
                "success": True,
                "updated_count": count,
                "message": f"Úspěšně aktualizováno {count} transakcí.",
            }
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get aggregated transaction statistics.

        GET /api/v1/transactions/stats/?date_from=2024-01-01&date_to=2024-12-31
        """
        qs = self.get_queryset()

        # Basic aggregates
        totals = qs.aggregate(
            total_count=Count("id"),
            total_income=Coalesce(Sum("castka", filter=Q(castka__gt=0)), Decimal("0")),
            total_expense=Coalesce(Sum("castka", filter=Q(castka__lt=0)), Decimal("0")),
        )
        totals["net_balance"] = totals["total_income"] + totals["total_expense"]

        # By status
        status_counts = dict(
            qs.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        # By KMEN (weighted by percentage)
        by_kmen = {
            "MH": qs.aggregate(
                total=Coalesce(Sum(F("castka") * F("mh_pct") / 100), Decimal("0"))
            )["total"],
            "SK": qs.aggregate(
                total=Coalesce(Sum(F("castka") * F("sk_pct") / 100), Decimal("0"))
            )["total"],
            "XP": qs.aggregate(
                total=Coalesce(Sum(F("castka") * F("xp_pct") / 100), Decimal("0"))
            )["total"],
            "FR": qs.aggregate(
                total=Coalesce(Sum(F("castka") * F("fr_pct") / 100), Decimal("0"))
            )["total"],
        }

        # By Druh
        by_druh = dict(
            qs.exclude(druh="")
            .values("druh")
            .annotate(total=Sum("castka"))
            .values_list("druh", "total")
        )

        # Uncategorized
        uncategorized = qs.filter(Q(prijem_vydaj="") | Q(druh="")).aggregate(
            count=Count("id"), amount=Coalesce(Sum("castka"), Decimal("0"))
        )

        stats_data = {
            "total_count": totals["total_count"],
            "total_income": totals["total_income"],
            "total_expense": abs(totals["total_expense"]),
            "net_balance": totals["net_balance"],
            "by_status": status_counts,
            "by_kmen": by_kmen,
            "by_druh": by_druh,
            "uncategorized_count": uncategorized["count"],
            "uncategorized_amount": uncategorized["amount"],
        }

        serializer = TransactionStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def trends(self, request):
        """
        Get monthly trend data.

        GET /api/v1/transactions/trends/?months=12
        """
        months = int(request.query_params.get("months", 12))
        qs = self.get_queryset()

        # Get monthly aggregates
        monthly_data = (
            qs.annotate(month=TruncMonth("datum"))
            .values("month")
            .annotate(
                income=Coalesce(Sum("castka", filter=Q(castka__gt=0)), Decimal("0")),
                expense=Coalesce(Sum("castka", filter=Q(castka__lt=0)), Decimal("0")),
                transaction_count=Count("id"),
            )
            .order_by("-month")[:months]
        )

        trends = []
        for item in monthly_data:
            trends.append(
                {
                    "month": item["month"],
                    "income": item["income"],
                    "expense": abs(item["expense"]),
                    "net": item["income"] + item["expense"],
                    "transaction_count": item["transaction_count"],
                }
            )

        serializer = MonthlyTrendSerializer(trends, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """
        Export transactions as CSV.

        GET /api/v1/transactions/export/?format=csv
        """
        import csv

        from django.http import HttpResponse

        qs = self.get_queryset()

        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = (
            'attachment; filename="transactions_export.csv"'
        )

        writer = csv.writer(response, delimiter=";")

        # Header row
        headers = [
            "Datum",
            "Účet",
            "Typ",
            "Poznámka/Zpráva",
            "VS",
            "Částka",
            "Status",
            "P/V",
            "V/N",
            "Daně",
            "Druh",
            "Detail",
            "KMEN",
            "MH%",
            "ŠK%",
            "XP%",
            "FR%",
            "Projekt",
            "Produkt",
            "Podskupina",
        ]
        writer.writerow(headers)

        # Data rows
        for t in qs.iterator():
            writer.writerow(
                [
                    t.datum.strftime("%d.%m.%Y") if t.datum else "",
                    t.ucet,
                    t.typ,
                    t.poznamka_zprava,
                    t.variabilni_symbol,
                    str(t.castka).replace(".", ","),
                    t.get_status_display(),
                    t.prijem_vydaj,
                    t.vlastni_nevlastni,
                    "Ano" if t.dane else "Ne",
                    t.druh,
                    t.detail,
                    t.kmen,
                    str(t.mh_pct).replace(".", ","),
                    str(t.sk_pct).replace(".", ","),
                    str(t.xp_pct).replace(".", ","),
                    str(t.fr_pct).replace(".", ","),
                    t.projekt.name if t.projekt else "",
                    t.produkt.name if t.produkt else "",
                    t.podskupina.name if t.podskupina else "",
                ]
            )

        return response


# =============================================================================
# CATEGORY RULE VIEWSET
# =============================================================================


class CategoryRuleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for CategoryRule management.

    list: Get all rules ordered by match_type and priority
    create: Create new rule
    update: Update rule
    delete: Delete or deactivate rule
    test: Test a rule against sample transactions
    apply: Apply rules to uncategorized transactions
    """

    queryset = CategoryRule.objects.select_related(
        "set_projekt", "set_produkt", "set_podskupina", "created_by"
    ).order_by("match_type", "priority", "name")
    serializer_class = CategoryRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["match_type", "match_mode", "is_active"]
    search_fields = ["name", "description", "match_value"]

    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """
        Test a rule against transactions.

        POST /api/v1/category-rules/{id}/test/
        Returns count of transactions that would match.
        """
        rule = self.get_object()
        importer = TransactionImporter(user=request.user)
        importer._load_caches()

        # Find matching transactions
        qs = Transaction.objects.all()
        match_count = 0
        sample_matches = []

        for txn in qs[:1000]:  # Limit to first 1000 for performance
            search_value = ""
            if rule.match_type == CategoryRule.MatchType.PROTIUCET:
                search_value = txn.cislo_protiuctu or ""
            elif rule.match_type == CategoryRule.MatchType.MERCHANT:
                search_value = txn.nazev_merchanta or ""
            elif rule.match_type == CategoryRule.MatchType.KEYWORD:
                search_value = " ".join(
                    filter(
                        None,
                        [
                            txn.poznamka_zprava,
                            txn.vlastni_poznamka,
                            txn.nazev_protiuctu,
                        ],
                    )
                )

            if search_value and importer._rule_matches(rule, search_value):
                match_count += 1
                if len(sample_matches) < 5:
                    sample_matches.append(
                        {
                            "id": str(txn.id),
                            "datum": txn.datum,
                            "castka": txn.castka,
                            "matched_text": search_value[:100],
                        }
                    )

        return Response(
            {
                "rule_id": str(rule.id),
                "rule_name": rule.name,
                "match_count": match_count,
                "sample_matches": sample_matches,
            }
        )

    @action(detail=False, methods=["post"])
    def apply_to_uncategorized(self, request):
        """
        Apply all active rules to uncategorized transactions.

        POST /api/v1/category-rules/apply_to_uncategorized/
        """
        importer = TransactionImporter(user=request.user)
        importer._load_caches()

        # Find uncategorized transactions
        uncategorized = Transaction.objects.filter(Q(prijem_vydaj="") | Q(druh=""))

        updated_count = 0
        for txn in uncategorized:
            original_status = (txn.prijem_vydaj, txn.druh)
            txn = importer.apply_autodetection_rules(txn)

            if (txn.prijem_vydaj, txn.druh) != original_status:
                txn.save()
                updated_count += 1

        return Response(
            {
                "success": True,
                "processed_count": uncategorized.count(),
                "updated_count": updated_count,
            }
        )


# =============================================================================
# IMPORT VIEWSET
# =============================================================================


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ImportBatch management.

    list: Get all import batches
    retrieve: Get single batch with error details
    upload: Upload and process new CSV file
    """

    queryset = ImportBatch.objects.select_related("created_by").order_by("-created_at")
    serializer_class = ImportBatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "total_rows", "imported_count"]

    @action(
        detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser]
    )
    def upload(self, request):
        """
        Upload and process a CSV file.

        POST /api/v1/imports/upload/
        Content-Type: multipart/form-data
        file: <csv_file>
        """
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        # Process the import
        importer = TransactionImporter(user=request.user)

        try:
            summary = importer.import_csv(
                file_stream=uploaded_file,
                filename=uploaded_file.name,
            )

            return Response(
                {
                    "success": True,
                    "batch_id": str(summary.batch_id),
                    "total_rows": summary.total_rows,
                    "imported": summary.imported,
                    "skipped": summary.skipped,
                    "errors": summary.errors,
                    "duration_seconds": summary.duration_seconds,
                    "error_details": summary.error_details[:10],  # First 10 errors
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """
        Get transactions from a specific import batch.

        GET /api/v1/imports/{id}/transactions/
        """
        batch = self.get_object()
        transactions = Transaction.objects.filter(import_batch=batch).order_by("datum")

        serializer = TransactionListSerializer(transactions, many=True)
        return Response(serializer.data)
