"""
Management command to display transaction statistics.

Usage:
    python manage.py transaction_stats
    python manage.py transaction_stats --date-from=2024-01-01
    python manage.py transaction_stats --by-month
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth

from apps.transactions.models import Transaction


class Command(BaseCommand):
    help = "Display transaction statistics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date-from",
            type=str,
            help="Filter from date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--date-to",
            type=str,
            help="Filter to date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--by-month",
            action="store_true",
            help="Show breakdown by month",
        )
        parser.add_argument(
            "--by-kmen",
            action="store_true",
            help="Show breakdown by KMEN",
        )
        parser.add_argument(
            "--by-druh",
            action="store_true",
            help="Show breakdown by Druh",
        )

    def handle(self, *args, **options):
        qs = Transaction.objects.all()

        # Apply date filters
        if options["date_from"]:
            qs = qs.filter(datum__gte=options["date_from"])
            self.stdout.write(f"From: {options['date_from']}")
        if options["date_to"]:
            qs = qs.filter(datum__lte=options["date_to"])
            self.stdout.write(f"To: {options['date_to']}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TRANSACTION STATISTICS")
        self.stdout.write("=" * 60)

        # Basic counts
        total = qs.count()
        self.stdout.write(f"\nTotal transactions: {total}")

        if total == 0:
            self.stdout.write(self.style.WARNING("No transactions found"))
            return

        # Status breakdown
        self.stdout.write("\n--- By Status ---")
        for status_value, status_label in Transaction.Status.choices:
            count = qs.filter(status=status_value).count()
            pct = (count / total * 100) if total else 0
            self.stdout.write(f"  {status_label}: {count} ({pct:.1f}%)")

        # Financial totals
        totals = qs.aggregate(
            income=Coalesce(Sum("castka", filter=Q(castka__gt=0)), Decimal("0")),
            expense=Coalesce(Sum("castka", filter=Q(castka__lt=0)), Decimal("0")),
        )
        income = totals["income"]
        expense = abs(totals["expense"])
        net = income - expense

        self.stdout.write("\n--- Financial Summary ---")
        self.stdout.write(f"  Income:  {income:>15,.2f} CZK")
        self.stdout.write(f"  Expense: {expense:>15,.2f} CZK")
        self.stdout.write(f"  Net:     {net:>15,.2f} CZK")

        # Categorization stats
        uncategorized = qs.filter(Q(prijem_vydaj="") | Q(druh="")).count()
        categorized = total - uncategorized

        self.stdout.write("\n--- Categorization ---")
        self.stdout.write(
            f"  Categorized:   {categorized} ({categorized/total*100:.1f}%)"
        )
        self.stdout.write(
            f"  Uncategorized: {uncategorized} ({uncategorized/total*100:.1f}%)"
        )

        # Optional breakdowns
        if options["by_month"]:
            self._show_by_month(qs)

        if options["by_kmen"]:
            self._show_by_kmen(qs)

        if options["by_druh"]:
            self._show_by_druh(qs)

        self.stdout.write("\n" + "=" * 60)

    def _show_by_month(self, qs):
        """Show monthly breakdown."""
        self.stdout.write("\n--- By Month ---")

        monthly = (
            qs.annotate(month=TruncMonth("datum"))
            .values("month")
            .annotate(
                count=Count("id"),
                income=Coalesce(Sum("castka", filter=Q(castka__gt=0)), Decimal("0")),
                expense=Coalesce(Sum("castka", filter=Q(castka__lt=0)), Decimal("0")),
            )
            .order_by("-month")[:12]
        )

        self.stdout.write(
            f"  {'Month':<12} {'Count':>8} {'Income':>15} {'Expense':>15} {'Net':>15}"
        )
        self.stdout.write("  " + "-" * 66)

        for row in monthly:
            month_str = row["month"].strftime("%Y-%m") if row["month"] else "Unknown"
            net = row["income"] + row["expense"]
            self.stdout.write(
                f"  {month_str:<12} {row['count']:>8} "
                f"{row['income']:>15,.0f} {abs(row['expense']):>15,.0f} {net:>15,.0f}"
            )

    def _show_by_kmen(self, qs):
        """Show KMEN breakdown (weighted by percentages)."""
        self.stdout.write("\n--- By KMEN ---")

        for kmen in ["MH", "SK", "XP", "FR"]:
            pct_field = f"{kmen.lower()}_pct"

            total = qs.aggregate(
                total=Coalesce(Sum(F("castka") * F(pct_field) / 100), Decimal("0"))
            )["total"]

            self.stdout.write(f"  {kmen}: {total:>15,.2f} CZK")

    def _show_by_druh(self, qs):
        """Show breakdown by Druh."""
        self.stdout.write("\n--- By Druh ---")

        by_druh = (
            qs.exclude(druh="")
            .values("druh")
            .annotate(
                count=Count("id"),
                total=Sum("castka"),
            )
            .order_by("-count")[:15]
        )

        self.stdout.write(f"  {'Druh':<25} {'Count':>8} {'Total':>15}")
        self.stdout.write("  " + "-" * 50)

        for row in by_druh:
            self.stdout.write(
                f"  {row['druh'][:25]:<25} {row['count']:>8} {row['total']:>15,.0f}"
            )
