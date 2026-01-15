"""
Mise HERo Finance - Transaction Filters
========================================
Django-filter FilterSets for transaction queries.
"""

import django_filters
from django.db.models import Q

from .models import Product, Project, Transaction


class TransactionFilter(django_filters.FilterSet):
    """
    Advanced filtering for Transaction queryset.

    Supports:
    - Date range filtering
    - Amount range filtering
    - Status and categorization filters
    - Project/Product hierarchy filters
    - Text search across multiple fields
    """

    # Date range
    date_from = django_filters.DateFilter(field_name="datum", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="datum", lookup_expr="lte")

    # Amount range
    amount_min = django_filters.NumberFilter(field_name="castka", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="castka", lookup_expr="lte")

    # Exact filters
    status = django_filters.ChoiceFilter(choices=Transaction.Status.choices)
    prijem_vydaj = django_filters.ChoiceFilter(choices=Transaction.PrijemVydaj.choices)
    vlastni_nevlastni = django_filters.ChoiceFilter(
        choices=Transaction.VlastniNevlastni.choices
    )
    kmen = django_filters.ChoiceFilter(choices=Transaction.Kmen.choices)

    # Boolean filters
    dane = django_filters.BooleanFilter()
    is_categorized = django_filters.BooleanFilter(method="filter_is_categorized")
    has_kmen_split = django_filters.BooleanFilter(method="filter_has_kmen_split")

    # Related filters
    projekt = django_filters.ModelChoiceFilter(
        queryset=Project.objects.filter(is_active=True)
    )
    produkt = django_filters.ModelChoiceFilter(
        queryset=Product.objects.filter(is_active=True)
    )
    import_batch = django_filters.UUIDFilter()

    # Text filters
    druh = django_filters.CharFilter(lookup_expr="icontains")
    detail = django_filters.CharFilter(lookup_expr="icontains")
    ucet = django_filters.CharFilter(lookup_expr="exact")

    # Multi-field search
    search = django_filters.CharFilter(method="filter_search")

    # Counterparty search
    protiucet = django_filters.CharFilter(method="filter_protiucet")

    class Meta:
        model = Transaction
        fields = [
            "date_from",
            "date_to",
            "amount_min",
            "amount_max",
            "status",
            "prijem_vydaj",
            "vlastni_nevlastni",
            "kmen",
            "dane",
            "is_categorized",
            "has_kmen_split",
            "projekt",
            "produkt",
            "import_batch",
            "druh",
            "detail",
            "ucet",
            "search",
            "protiucet",
        ]

    def filter_is_categorized(self, queryset, name, value):
        """Filter by whether transaction is categorized."""
        if value:
            # Categorized: has both P/V and druh
            return queryset.exclude(Q(prijem_vydaj="") | Q(druh=""))
        else:
            # Uncategorized: missing P/V or druh
            return queryset.filter(Q(prijem_vydaj="") | Q(druh=""))

    def filter_has_kmen_split(self, queryset, name, value):
        """Filter by whether KMEN split is assigned."""
        from decimal import Decimal

        from django.db.models import F

        if value:
            # Has split: percentages sum to 100
            return queryset.annotate(
                pct_sum=F("mh_pct") + F("sk_pct") + F("xp_pct") + F("fr_pct")
            ).filter(pct_sum=Decimal("100"))
        else:
            # No split: percentages sum to 0 or not 100
            return queryset.annotate(
                pct_sum=F("mh_pct") + F("sk_pct") + F("xp_pct") + F("fr_pct")
            ).exclude(pct_sum=Decimal("100"))

    def filter_search(self, queryset, name, value):
        """
        Multi-field text search.
        Searches: poznámka, název protiúčtu, merchant, VS, vlastní poznámka
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(poznamka_zprava__icontains=value)
            | Q(nazev_protiuctu__icontains=value)
            | Q(nazev_merchanta__icontains=value)
            | Q(variabilni_symbol__icontains=value)
            | Q(vlastni_poznamka__icontains=value)
            | Q(detail__icontains=value)
        )

    def filter_protiucet(self, queryset, name, value):
        """
        Search by counterparty (account number or name).
        """
        if not value:
            return queryset

        return queryset.filter(
            Q(cislo_protiuctu__icontains=value) | Q(nazev_protiuctu__icontains=value)
        )


class TransactionExportFilter(TransactionFilter):
    """
    Extended filter for transaction export.
    Adds date range presets.
    """

    PRESET_CHOICES = [
        ("this_month", "Tento měsíc"),
        ("last_month", "Minulý měsíc"),
        ("this_quarter", "Toto čtvrtletí"),
        ("last_quarter", "Minulé čtvrtletí"),
        ("this_year", "Tento rok"),
        ("last_year", "Minulý rok"),
    ]

    date_preset = django_filters.ChoiceFilter(
        choices=PRESET_CHOICES, method="filter_date_preset"
    )

    def filter_date_preset(self, queryset, name, value):
        """Apply date range based on preset."""
        from datetime import date

        from dateutil.relativedelta import relativedelta

        today = date.today()

        if value == "this_month":
            start = today.replace(day=1)
            end = today
        elif value == "last_month":
            start = today.replace(day=1) - relativedelta(months=1)
            end = today.replace(day=1) - relativedelta(days=1)
        elif value == "this_quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=quarter_month, day=1)
            end = today
        elif value == "last_quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            end = today.replace(month=quarter_month, day=1) - relativedelta(days=1)
            start = end.replace(day=1) - relativedelta(months=2)
        elif value == "this_year":
            start = today.replace(month=1, day=1)
            end = today
        elif value == "last_year":
            start = today.replace(year=today.year - 1, month=1, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            return queryset

        return queryset.filter(datum__gte=start, datum__lte=end)
