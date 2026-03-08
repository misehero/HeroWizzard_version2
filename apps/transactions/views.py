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
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .filters import TransactionFilter
from .models import (CategoryRule, CostDetail, ImportBatch, Product,
                     ProductSubgroup, Project, Transaction,
                     TransactionAuditLog)
from .serializers import (CategoryRuleSerializer, CostDetailSerializer,
                          CSVUploadSerializer, ImportBatchSerializer,
                          ManualTransactionSerializer,
                          MonthlyTrendSerializer, ProductSerializer,
                          ProductSubgroupDetailSerializer, ProjectSerializer,
                          TransactionAuditLogSerializer,
                          TransactionBulkUpdateSerializer,
                          TransactionDetailSerializer,
                          TransactionListSerializer,
                          TransactionStatsSerializer)
from .services import IDokladImporter, TransactionImporter

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
    ordering_fields = ["sort_order", "name", "created_at"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        """Filter to active projects unless ?include_inactive=true or detail view."""
        qs = super().get_queryset()
        # Don't filter on detail actions (retrieve, update, partial_update, destroy)
        if self.action == "list" and not self.request.query_params.get("include_inactive"):
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
    ordering_fields = ["sort_order", "category", "name", "created_at"]
    ordering = ["sort_order", "category", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list" and not self.request.query_params.get("include_inactive"):
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
        if self.action == "list" and not self.request.query_params.get("include_inactive"):
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
        "projekt", "produkt", "podskupina", "updated_by"
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
        """Apply date range, is_active, and is_deleted filters."""
        qs = super().get_queryset()

        # Always exclude soft-deleted transactions
        qs = qs.filter(is_deleted=False)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            qs = qs.filter(datum__gte=date_from)
        if date_to:
            qs = qs.filter(datum__lte=date_to)

        # Active/inactive filtering: only on list/stats/trends, not on retrieve/update
        if self.action in ("list", "stats", "trends"):
            show_inactive = self.request.query_params.get("show_inactive")
            if show_inactive not in ("true", "1"):
                qs = qs.filter(is_active=True)

        return qs

    @staticmethod
    def _format_audit_value(val):
        """Format a value for audit log display."""
        if val is None or val == "":
            return "—"
        if isinstance(val, bool):
            return "Ano" if val else "Ne"
        return str(val)

    def perform_update(self, serializer):
        """Set updated_by and create audit log on every update."""
        instance = serializer.instance

        # Capture changes before save
        fmt = self._format_audit_value
        changes = []
        for field_name, new_val in serializer.validated_data.items():
            old_val = getattr(instance, field_name)
            old_str = fmt(old_val)
            new_str = fmt(new_val)
            if old_str != new_str:
                try:
                    verbose = instance._meta.get_field(field_name).verbose_name
                except Exception:
                    verbose = field_name
                changes.append(f"{verbose}: {old_str} → {new_str}")

        serializer.save(updated_by=self.request.user)

        if changes:
            TransactionAuditLog.objects.create(
                transaction=instance,
                user=self.request.user,
                action="Úprava",
                details="; ".join(changes),
            )

    @action(detail=True, methods=["get"], url_path="audit-log")
    def audit_log(self, request, pk=None):
        """
        Get audit log entries for a specific transaction.

        GET /api/v1/transactions/{id}/audit-log/
        """
        transaction = self.get_object()
        logs = TransactionAuditLog.objects.filter(
            transaction=transaction
        ).select_related("user")
        serializer = TransactionAuditLogSerializer(logs, many=True)
        return Response(serializer.data)

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

        qs = self.filter_queryset(self.get_queryset())

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

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        """
        Export filtered transactions as Excel (.xlsx).

        GET /api/v1/transactions/export-excel/?status=...&prijem_vydaj=...&date_from=...&date_to=...&search=...
        """
        from io import BytesIO

        from django.http import HttpResponse
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        qs = self.filter_queryset(self.get_queryset())
        # Always exclude inactive transactions from Excel export
        qs = qs.filter(is_active=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Transakce"

        # Header style
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")

        headers = [
            "Datum", "Účet", "Typ", "Poznámka/Zpráva", "VS",
            "Částka", "Číslo protiúčtu", "Název protiúčtu",
            "Název obchodníka", "Město", "Status", "P/V", "V/N",
            "Daně", "Druh", "Detail", "KMEN", "MH%", "ŠK%", "XP%", "FR%",
            "Projekt", "Produkt", "Podskupina",
        ]

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # Data rows
        for row_idx, t in enumerate(qs.iterator(), 2):
            ws.cell(row=row_idx, column=1, value=t.datum.strftime("%d.%m.%Y") if t.datum else "")
            ws.cell(row=row_idx, column=2, value=t.ucet or "")
            ws.cell(row=row_idx, column=3, value=t.typ or "")
            ws.cell(row=row_idx, column=4, value=t.poznamka_zprava or "")
            ws.cell(row=row_idx, column=5, value=t.variabilni_symbol or "")
            ws.cell(row=row_idx, column=6, value=float(t.castka) if t.castka else 0)
            ws.cell(row=row_idx, column=7, value=t.cislo_protiuctu or "")
            ws.cell(row=row_idx, column=8, value=t.nazev_protiuctu or "")
            ws.cell(row=row_idx, column=9, value=t.nazev_merchanta or "")
            ws.cell(row=row_idx, column=10, value=t.mesto or "")
            ws.cell(row=row_idx, column=11, value=t.get_status_display())
            ws.cell(row=row_idx, column=12, value=t.prijem_vydaj or "")
            ws.cell(row=row_idx, column=13, value=t.vlastni_nevlastni or "")
            ws.cell(row=row_idx, column=14, value="Ano" if t.dane else "Ne")
            ws.cell(row=row_idx, column=15, value=t.druh or "")
            ws.cell(row=row_idx, column=16, value=t.detail or "")
            ws.cell(row=row_idx, column=17, value=t.kmen or "")
            ws.cell(row=row_idx, column=18, value=float(t.mh_pct))
            ws.cell(row=row_idx, column=19, value=float(t.sk_pct))
            ws.cell(row=row_idx, column=20, value=float(t.xp_pct))
            ws.cell(row=row_idx, column=21, value=float(t.fr_pct))
            ws.cell(row=row_idx, column=22, value=t.projekt.name if t.projekt else "")
            ws.cell(row=row_idx, column=23, value=t.produkt.name if t.produkt else "")
            ws.cell(row=row_idx, column=24, value=t.podskupina.name if t.podskupina else "")

        # Auto-width columns
        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            max_length = len(str(headers[col_idx - 1]))
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)

        # Number format for amount column
        for row in ws.iter_rows(min_row=2, min_col=6, max_col=6):
            for cell in row:
                cell.number_format = '#,##0.00'

        # Freeze header row
        ws.freeze_panes = "A2"

        # Write to response
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="transakce_export.xlsx"'
        return response

    @action(detail=False, methods=["post"], url_path="create-manual")
    def create_manual(self, request):
        """
        Manually create a single transaction.

        POST /api/v1/transactions/create-manual/
        Allows setting key bank columns (datum, castka, …) that are
        read-only on the standard update serializer.
        """
        serializer = ManualTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transaction = serializer.save(
            created_by=request.user,
            updated_by=request.user,
            status="upraveno",
            mena="CZK",
        )

        # Auto-set P/V from amount sign when not explicitly provided
        if not transaction.prijem_vydaj:
            transaction.prijem_vydaj = "P" if transaction.castka > 0 else "V"
            transaction.save(update_fields=["prijem_vydaj"])

        TransactionAuditLog.objects.create(
            transaction=transaction,
            user=request.user,
            action="Ruční vytvoření",
            details="",
        )

        return Response(
            TransactionDetailSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="export-backup",
        permission_classes=[IsAdminUser],
    )
    def export_backup(self, request):
        """
        Export full application state as JSON backup (admin only).
        Includes: lookups, transactions, category rules, audit logs, import batches.

        GET /api/v1/transactions/export-backup/
        """
        import json

        from django.http import HttpResponse

        # --- Transactions ---
        txn_qs = (
            Transaction.objects.filter(is_deleted=False)
            .select_related("projekt", "produkt", "podskupina")
            .order_by("datum", "created_at")
        )
        txn_records = []
        for t in txn_qs.iterator():
            txn_records.append(
                {
                    "id": str(t.id),
                    "datum": t.datum.isoformat() if t.datum else None,
                    "ucet": t.ucet,
                    "typ": t.typ,
                    "poznamka_zprava": t.poznamka_zprava,
                    "variabilni_symbol": t.variabilni_symbol,
                    "castka": str(t.castka),
                    "datum_zauctovani": (
                        t.datum_zauctovani.isoformat() if t.datum_zauctovani else None
                    ),
                    "cislo_protiuctu": t.cislo_protiuctu,
                    "nazev_protiuctu": t.nazev_protiuctu,
                    "typ_transakce": t.typ_transakce,
                    "konstantni_symbol": t.konstantni_symbol,
                    "specificky_symbol": t.specificky_symbol,
                    "puvodni_castka": str(t.puvodni_castka) if t.puvodni_castka else None,
                    "puvodni_mena": t.puvodni_mena,
                    "poplatky": str(t.poplatky) if t.poplatky else None,
                    "id_transakce": t.id_transakce,
                    "vlastni_poznamka": t.vlastni_poznamka,
                    "nazev_merchanta": t.nazev_merchanta,
                    "mesto": t.mesto,
                    "mena": t.mena,
                    "banka_protiuctu": t.banka_protiuctu,
                    "reference": t.reference,
                    "status": t.status,
                    "prijem_vydaj": t.prijem_vydaj,
                    "vlastni_nevlastni": t.vlastni_nevlastni,
                    "dane": t.dane,
                    "druh": t.druh,
                    "detail": t.detail,
                    "kmen": t.kmen,
                    "mh_pct": str(t.mh_pct),
                    "sk_pct": str(t.sk_pct),
                    "xp_pct": str(t.xp_pct),
                    "fr_pct": str(t.fr_pct),
                    "projekt": t.projekt.name if t.projekt else None,
                    "produkt": t.produkt.name if t.produkt else None,
                    "podskupina": t.podskupina.name if t.podskupina else None,
                    "is_active": t.is_active,
                    "import_batch_id": str(t.import_batch_id) if t.import_batch_id else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
            )

        # --- Category Rules ---
        rule_records = []
        for r in CategoryRule.objects.select_related(
            "set_projekt", "set_produkt", "set_podskupina"
        ).order_by("match_type", "priority"):
            rule_records.append(
                {
                    "id": str(r.id),
                    "name": r.name,
                    "description": r.description,
                    "match_type": r.match_type,
                    "match_mode": r.match_mode,
                    "match_value": r.match_value,
                    "case_sensitive": r.case_sensitive,
                    "priority": r.priority,
                    "set_prijem_vydaj": r.set_prijem_vydaj,
                    "set_vlastni_nevlastni": r.set_vlastni_nevlastni,
                    "set_dane": r.set_dane,
                    "set_druh": r.set_druh,
                    "set_detail": r.set_detail,
                    "set_kmen": r.set_kmen,
                    "set_mh_pct": str(r.set_mh_pct) if r.set_mh_pct is not None else None,
                    "set_sk_pct": str(r.set_sk_pct) if r.set_sk_pct is not None else None,
                    "set_xp_pct": str(r.set_xp_pct) if r.set_xp_pct is not None else None,
                    "set_fr_pct": str(r.set_fr_pct) if r.set_fr_pct is not None else None,
                    "set_projekt": r.set_projekt.name if r.set_projekt else None,
                    "set_produkt": r.set_produkt.name if r.set_produkt else None,
                    "set_podskupina": r.set_podskupina.name if r.set_podskupina else None,
                    "is_active": r.is_active,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )

        # --- Import Batches ---
        batch_records = []
        for b in ImportBatch.objects.order_by("created_at"):
            batch_records.append(
                {
                    "id": str(b.id),
                    "filename": b.filename,
                    "status": b.status,
                    "total_rows": b.total_rows,
                    "imported_count": b.imported_count,
                    "skipped_count": b.skipped_count,
                    "error_count": b.error_count,
                    "error_details": b.error_details,
                    "started_at": b.started_at.isoformat() if b.started_at else None,
                    "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
            )

        # --- Audit Logs ---
        audit_records = []
        for a in TransactionAuditLog.objects.select_related("user").order_by("created_at"):
            audit_records.append(
                {
                    "id": str(a.id),
                    "transaction_id": str(a.transaction_id),
                    "user_email": a.user.email if a.user else None,
                    "action": a.action,
                    "details": a.details,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
            )

        # --- Lookups (Projects, Products, Subgroups) ---
        project_records = [
            {
                "id": p.id, "name": p.name, "description": p.description,
                "sort_order": p.sort_order, "is_active": p.is_active,
            }
            for p in Project.objects.order_by("sort_order", "name")
        ]
        product_records = [
            {
                "id": p.id, "name": p.name, "category": p.category,
                "description": p.description, "sort_order": p.sort_order,
                "is_active": p.is_active,
            }
            for p in Product.objects.order_by("sort_order", "category", "name")
        ]
        subgroup_records = [
            {
                "id": s.id, "product_id": s.product_id, "name": s.name,
                "description": s.description, "sort_order": s.sort_order,
                "is_active": s.is_active,
            }
            for s in ProductSubgroup.objects.order_by("product", "sort_order", "name")
        ]

        payload = json.dumps(
            {
                "version": 6,
                "projects": project_records,
                "products": product_records,
                "product_subgroups": subgroup_records,
                "transactions": txn_records,
                "category_rules": rule_records,
                "import_batches": batch_records,
                "audit_logs": audit_records,
                "counts": {
                    "projects": len(project_records),
                    "products": len(product_records),
                    "product_subgroups": len(subgroup_records),
                    "transactions": len(txn_records),
                    "category_rules": len(rule_records),
                    "import_batches": len(batch_records),
                    "audit_logs": len(audit_records),
                },
            },
            ensure_ascii=False,
            indent=2,
        )

        response = HttpResponse(payload, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="herowizzard_backup.json"'
        )
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import-backup",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAdminUser],
    )
    def import_backup(self, request):
        """
        Restore application state from a JSON backup file (admin only).
        DELETES all existing transactions, category rules, audit logs,
        and import batches, then recreates them from the backup.
        Users and roles are NOT affected.

        Supports both v3 (transactions only) and v5 (full backup) formats.

        POST /api/v1/transactions/import-backup/
        """
        import json

        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"success": False, "error": "Nebyl nahrán žádný soubor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = uploaded_file.read().decode("utf-8")
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return Response(
                {"success": False, "error": f"Neplatný JSON soubor: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._restore_from_data(request, data)

    def _restore_from_data(self, request, data):
        """Shared restore logic used by both import_backup and restore_server_backup."""
        import uuid as _uuid
        from datetime import date

        from django.db import connection, transaction as db_transaction
        from django.utils.dateparse import parse_datetime

        backup_version = data.get("version", 3)
        txn_records = data.get("transactions", [])
        rule_records = data.get("category_rules", [])
        batch_records = data.get("import_batches", [])
        audit_records = data.get("audit_logs", [])
        # v6+ lookups
        project_records = data.get("projects", [])
        product_records = data.get("products", [])
        subgroup_records = data.get("product_subgroups", [])

        if not txn_records and not rule_records:
            return Response(
                {"success": False, "error": "Záloha neobsahuje žádná data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve user by email for audit logs
        from apps.core.models import User

        user_map = {u.email: u for u in User.objects.all()}

        errors = []
        counts = {
            "transactions_deleted": 0,
            "transactions_imported": 0,
            "rules_deleted": 0,
            "rules_imported": 0,
            "batches_deleted": 0,
            "batches_imported": 0,
            "audit_logs_deleted": 0,
            "audit_logs_imported": 0,
            "projects_imported": 0,
            "products_imported": 0,
            "subgroups_imported": 0,
        }

        try:
            with db_transaction.atomic():
                # ---- PHASE 1: DELETE existing data ----
                counts["audit_logs_deleted"] = TransactionAuditLog.objects.count()
                counts["transactions_deleted"] = Transaction.objects.count()
                counts["batches_deleted"] = ImportBatch.objects.count()
                counts["rules_deleted"] = CategoryRule.objects.count()
                # Use TRUNCATE CASCADE to handle FK constraints at DB level
                from django.db import connection as db_conn

                has_lookups = bool(project_records or product_records or subgroup_records)
                with db_conn.cursor() as cursor:
                    tables = (
                        "transactions_audit_log, "
                        "transactions_transaction, "
                        "transactions_import_batch, "
                        "transactions_category_rule"
                    )
                    if has_lookups:
                        tables += (
                            ", transactions_product_subgroup"
                            ", transactions_product"
                            ", transactions_project"
                        )
                    cursor.execute(f"TRUNCATE TABLE {tables} CASCADE")

                # ---- PHASE 1b: Restore lookups (v6+) ----
                if project_records:
                    for rec in project_records:
                        try:
                            Project.objects.create(
                                id=rec["id"], name=rec["name"],
                                description=rec.get("description", ""),
                                sort_order=rec.get("sort_order", 0),
                                is_active=rec.get("is_active", True),
                            )
                            counts["projects_imported"] += 1
                        except Exception as e:
                            errors.append({"type": "project", "id": rec.get("id"), "error": str(e)})

                if product_records:
                    for rec in product_records:
                        try:
                            Product.objects.create(
                                id=rec["id"], name=rec["name"],
                                category=rec.get("category", "SKOLY"),
                                description=rec.get("description", ""),
                                sort_order=rec.get("sort_order", 0),
                                is_active=rec.get("is_active", True),
                            )
                            counts["products_imported"] += 1
                        except Exception as e:
                            errors.append({"type": "product", "id": rec.get("id"), "error": str(e)})

                if subgroup_records:
                    for rec in subgroup_records:
                        try:
                            ProductSubgroup.objects.create(
                                id=rec["id"], product_id=rec["product_id"],
                                name=rec["name"],
                                description=rec.get("description", ""),
                                sort_order=rec.get("sort_order", 0),
                                is_active=rec.get("is_active", True),
                            )
                            counts["subgroups_imported"] += 1
                        except Exception as e:
                            errors.append({"type": "subgroup", "id": rec.get("id"), "error": str(e)})

                # Build lookup maps after restore
                project_map = {p.name: p for p in Project.objects.all()}
                product_map = {p.name: p for p in Product.objects.all()}
                subgroup_map = {s.name: s for s in ProductSubgroup.objects.all()}

                # ---- PHASE 2: Restore import batches first (transactions reference them) ----
                for rec in batch_records:
                    try:
                        batch = ImportBatch(
                            id=_uuid.UUID(rec["id"]),
                            filename=rec.get("filename", ""),
                            status=rec.get("status", "completed"),
                            total_rows=rec.get("total_rows", 0),
                            imported_count=rec.get("imported_count", 0),
                            skipped_count=rec.get("skipped_count", 0),
                            error_count=rec.get("error_count", 0),
                            error_details=rec.get("error_details", []),
                        )
                        batch.save()
                        # Update timestamps via raw SQL (auto_now_add prevents direct set)
                        if rec.get("created_at"):
                            ImportBatch.objects.filter(id=batch.id).update(
                                created_at=parse_datetime(rec["created_at"]),
                                started_at=parse_datetime(rec["started_at"]) if rec.get("started_at") else None,
                                completed_at=parse_datetime(rec["completed_at"]) if rec.get("completed_at") else None,
                            )
                        counts["batches_imported"] += 1
                    except Exception as e:
                        errors.append({"type": "batch", "id": rec.get("id"), "error": str(e)})

                # ---- PHASE 3: Restore category rules ----
                for rec in rule_records:
                    try:
                        rule = CategoryRule(
                            id=_uuid.UUID(rec["id"]),
                            name=rec.get("name", ""),
                            description=rec.get("description", ""),
                            match_type=rec.get("match_type", ""),
                            match_mode=rec.get("match_mode", "exact"),
                            match_value=rec.get("match_value", ""),
                            case_sensitive=rec.get("case_sensitive", False),
                            priority=rec.get("priority", 100),
                            set_prijem_vydaj=rec.get("set_prijem_vydaj", ""),
                            set_vlastni_nevlastni=rec.get("set_vlastni_nevlastni", ""),
                            set_dane=rec.get("set_dane"),
                            set_druh=rec.get("set_druh", ""),
                            set_detail=rec.get("set_detail", ""),
                            set_kmen=rec.get("set_kmen", ""),
                            set_mh_pct=Decimal(rec["set_mh_pct"]) if rec.get("set_mh_pct") is not None else None,
                            set_sk_pct=Decimal(rec["set_sk_pct"]) if rec.get("set_sk_pct") is not None else None,
                            set_xp_pct=Decimal(rec["set_xp_pct"]) if rec.get("set_xp_pct") is not None else None,
                            set_fr_pct=Decimal(rec["set_fr_pct"]) if rec.get("set_fr_pct") is not None else None,
                            is_active=rec.get("is_active", True),
                            created_by=request.user,
                        )
                        if rec.get("set_projekt"):
                            rule.set_projekt = project_map.get(rec["set_projekt"])
                        if rec.get("set_produkt"):
                            rule.set_produkt = product_map.get(rec["set_produkt"])
                        if rec.get("set_podskupina"):
                            rule.set_podskupina = subgroup_map.get(rec["set_podskupina"])
                        rule.save()
                        # Restore original created_at
                        if rec.get("created_at"):
                            CategoryRule.objects.filter(id=rule.id).update(
                                created_at=parse_datetime(rec["created_at"])
                            )
                        counts["rules_imported"] += 1
                    except Exception as e:
                        errors.append({"type": "rule", "id": rec.get("id"), "error": str(e)})

                # ---- PHASE 4: Restore transactions ----
                for idx, rec in enumerate(txn_records, 1):
                    try:
                        txn = Transaction()
                        rec_id = rec.get("id", "")
                        if rec_id:
                            txn.id = _uuid.UUID(rec_id)
                        txn.datum = date.fromisoformat(rec["datum"]) if rec.get("datum") else None
                        txn.ucet = rec.get("ucet", "")
                        txn.typ = rec.get("typ", "")
                        txn.poznamka_zprava = rec.get("poznamka_zprava", "")
                        txn.variabilni_symbol = rec.get("variabilni_symbol", "")
                        txn.castka = Decimal(rec["castka"]) if rec.get("castka") else Decimal("0")
                        txn.datum_zauctovani = (
                            date.fromisoformat(rec["datum_zauctovani"])
                            if rec.get("datum_zauctovani") else None
                        )
                        txn.cislo_protiuctu = rec.get("cislo_protiuctu", "")
                        txn.nazev_protiuctu = rec.get("nazev_protiuctu", "")
                        txn.typ_transakce = rec.get("typ_transakce", "")
                        txn.konstantni_symbol = rec.get("konstantni_symbol", "")
                        txn.specificky_symbol = rec.get("specificky_symbol", "")
                        txn.puvodni_castka = (
                            Decimal(rec["puvodni_castka"]) if rec.get("puvodni_castka") else None
                        )
                        txn.puvodni_mena = rec.get("puvodni_mena", "")
                        txn.poplatky = Decimal(rec["poplatky"]) if rec.get("poplatky") else None
                        txn.id_transakce = rec.get("id_transakce", "")
                        txn.vlastni_poznamka = rec.get("vlastni_poznamka", "")
                        txn.nazev_merchanta = rec.get("nazev_merchanta", "")
                        txn.mesto = rec.get("mesto", "")
                        txn.mena = rec.get("mena", "CZK")
                        txn.banka_protiuctu = rec.get("banka_protiuctu", "")
                        txn.reference = rec.get("reference", "")
                        txn.status = rec.get("status", "")
                        txn.prijem_vydaj = rec.get("prijem_vydaj", "")
                        txn.vlastni_nevlastni = rec.get("vlastni_nevlastni", "")
                        txn.dane = rec.get("dane", False)
                        txn.druh = rec.get("druh", "")
                        txn.detail = rec.get("detail", "")
                        txn.kmen = rec.get("kmen", "")
                        txn.mh_pct = Decimal(rec.get("mh_pct", "0"))
                        txn.sk_pct = Decimal(rec.get("sk_pct", "0"))
                        txn.xp_pct = Decimal(rec.get("xp_pct", "0"))
                        txn.fr_pct = Decimal(rec.get("fr_pct", "0"))
                        txn.is_active = rec.get("is_active", True)
                        txn.is_deleted = False
                        if rec.get("projekt"):
                            txn.projekt = project_map.get(rec["projekt"])
                        if rec.get("produkt"):
                            txn.produkt = product_map.get(rec["produkt"])
                        if rec.get("podskupina"):
                            txn.podskupina = subgroup_map.get(rec["podskupina"])
                        txn.created_by = request.user
                        if rec.get("import_batch_id"):
                            txn.import_batch_id = _uuid.UUID(rec["import_batch_id"])
                        txn.save()
                        # Restore original created_at
                        if rec.get("created_at"):
                            Transaction.objects.filter(id=txn.id).update(
                                created_at=parse_datetime(rec["created_at"])
                            )
                        counts["transactions_imported"] += 1
                    except Exception as e:
                        errors.append({"type": "transaction", "row": idx, "id": rec.get("id", ""), "error": str(e)})
                        if len(errors) > 50:
                            break

                # ---- PHASE 5: Restore audit logs ----
                # Build set of imported transaction IDs to skip orphaned audit logs
                # (e.g. logs for soft-deleted transactions not included in backup)
                imported_txn_ids = {
                    str(uid) for uid in
                    Transaction.objects.values_list("id", flat=True).iterator()
                }
                skipped_audit = 0
                for rec in audit_records:
                    try:
                        txn_id = rec.get("transaction_id", "")
                        if txn_id not in imported_txn_ids:
                            skipped_audit += 1
                            continue
                        log = TransactionAuditLog(
                            id=_uuid.UUID(rec["id"]),
                            transaction_id=_uuid.UUID(txn_id),
                            user=user_map.get(rec.get("user_email")),
                            action=rec.get("action", ""),
                            details=rec.get("details", ""),
                        )
                        log.save()
                        if rec.get("created_at"):
                            TransactionAuditLog.objects.filter(id=log.id).update(
                                created_at=parse_datetime(rec["created_at"])
                            )
                        counts["audit_logs_imported"] += 1
                    except Exception as e:
                        errors.append({"type": "audit_log", "id": rec.get("id"), "error": str(e)})
                if skipped_audit:
                    counts["audit_logs_skipped"] = skipped_audit

        except Exception as e:
            return Response(
                {"success": False, "error": f"Obnova selhala (rollback): {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "backup_version": backup_version,
                "counts": counts,
                "errors": len(errors),
                "error_details": errors[:10],
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="server-backups",
        permission_classes=[IsAdminUser],
    )
    def server_backups(self, request):
        """
        List available automatic backup files on the server (admin only).

        GET /api/v1/transactions/server-backups/
        """
        import os
        from datetime import datetime
        from pathlib import Path

        from django.conf import settings

        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        if not os.path.isdir(backup_dir):
            return Response({"backups": []})

        backups = []
        for f in sorted(
            Path(backup_dir).glob("backup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            stat = f.stat()
            backups.append(
                {
                    "filename": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return Response({"backups": backups})

    @action(
        detail=False,
        methods=["post"],
        url_path="restore-server-backup",
        permission_classes=[IsAdminUser],
    )
    def restore_server_backup(self, request):
        """
        Restore from a server-side automatic backup file (admin only).
        Expects JSON body: {"filename": "backup_2026-03-08_02-00.json"}

        POST /api/v1/transactions/restore-server-backup/
        """
        import json
        import os

        from django.conf import settings

        filename = request.data.get("filename", "")
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return Response(
                {"error": "Neplatný název souboru."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        filepath = os.path.join(backup_dir, filename)

        if not os.path.isfile(filepath):
            return Response(
                {"error": f"Soubor '{filename}' nebyl nalezen."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return Response(
                {"error": f"Soubor nelze přečíst: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._restore_from_data(request, data)

    @action(
        detail=False,
        methods=["post"],
        url_path="wipe-all",
        permission_classes=[IsAdminUser],
    )
    def wipe_all(self, request):
        """
        Soft-delete ALL non-deleted transactions (admin only).
        Sets is_deleted=True instead of actual deletion.

        POST /api/v1/transactions/wipe-all/
        """
        count = Transaction.objects.filter(is_deleted=False).update(is_deleted=True)

        return Response(
            {
                "success": True,
                "wiped_count": count,
                "message": f"Soft-deleted {count} transactions.",
            }
        )


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
        transactions = Transaction.objects.filter(import_batch_id=batch.id).order_by("datum")

        serializer = TransactionListSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-idoklad",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_idoklad(self, request):
        """
        Upload and process an iDoklad invoice CSV file.

        POST /api/v1/imports/upload-idoklad/
        Content-Type: multipart/form-data
        file: <csv_file>
        """
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        importer = IDokladImporter(user=request.user)

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
                    "error_details": summary.error_details[:10],
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
