"""Transactions app admin configuration."""

from django.contrib import admin

from .models import (CategoryRule, CostDetail, ImportBatch, Product,
                     ProductSubgroup, Project, Transaction)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("id", "name", "description")
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("id", "name", "description")
    ordering = ("category", "name")


@admin.register(ProductSubgroup)
class ProductSubgroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "product", "is_active")
    list_filter = ("product", "is_active")
    search_fields = ("id", "name")
    ordering = ("product", "name")


@admin.register(CostDetail)
class CostDetailAdmin(admin.ModelAdmin):
    list_display = ("id", "druh_type", "druh_value", "detail", "is_active")
    list_filter = ("druh_type", "is_active")
    search_fields = ("druh_value", "detail")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "datum",
        "castka",
        "status",
        "prijem_vydaj",
        "druh",
        "kmen",
        "projekt",
    )
    list_filter = (
        "status",
        "prijem_vydaj",
        "vlastni_nevlastni",
        "dane",
        "kmen",
        "projekt",
        "produkt",
    )
    search_fields = (
        "poznamka_zprava",
        "nazev_protiuctu",
        "nazev_merchanta",
        "id_transakce",
    )
    readonly_fields = (
        # Bank columns (non-editable)
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
        # Audit
        "import_batch_id",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "datum"
    ordering = ("-datum", "-created_at")

    fieldsets = (
        (
            "Bank Data (Read-Only)",
            {
                "fields": (
                    ("datum", "datum_zauctovani"),
                    ("ucet", "castka", "mena"),
                    ("typ", "typ_transakce"),
                    "poznamka_zprava",
                    ("variabilni_symbol", "konstantni_symbol", "specificky_symbol"),
                    ("cislo_protiuctu", "nazev_protiuctu", "banka_protiuctu"),
                    ("nazev_merchanta", "mesto"),
                    ("puvodni_castka", "puvodni_mena", "poplatky"),
                    ("id_transakce", "reference"),
                    "vlastni_poznamka",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Categorization",
            {
                "fields": (
                    "status",
                    ("prijem_vydaj", "vlastni_nevlastni", "dane"),
                    ("druh", "detail"),
                ),
            },
        ),
        (
            "KMEN Split",
            {
                "fields": (
                    "kmen",
                    ("mh_pct", "sk_pct", "xp_pct", "fr_pct"),
                ),
            },
        ),
        (
            "Project/Product Assignment",
            {
                "fields": (
                    "projekt",
                    ("produkt", "podskupina"),
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "import_batch_id",
                    ("created_at", "updated_at"),
                    ("created_by", "updated_by"),
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(CategoryRule)
class CategoryRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "match_type",
        "match_mode",
        "match_value",
        "priority",
        "is_active",
    )
    list_filter = ("match_type", "match_mode", "is_active")
    search_fields = ("name", "match_value", "description")
    ordering = ("match_type", "priority", "name")

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "description", "is_active", "priority"),
            },
        ),
        (
            "Matching Rules",
            {
                "fields": (
                    "match_type",
                    "match_mode",
                    "match_value",
                    "case_sensitive",
                ),
            },
        ),
        (
            "Category Assignments",
            {
                "fields": (
                    ("set_prijem_vydaj", "set_vlastni_nevlastni", "set_dane"),
                    ("set_druh", "set_detail"),
                ),
            },
        ),
        (
            "KMEN Split Assignments",
            {
                "fields": (
                    "set_kmen",
                    ("set_mh_pct", "set_sk_pct", "set_xp_pct", "set_fr_pct"),
                ),
            },
        ),
        (
            "Project/Product Assignments",
            {
                "fields": (
                    "set_projekt",
                    ("set_produkt", "set_podskupina"),
                ),
            },
        ),
    )


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "status",
        "total_rows",
        "imported_count",
        "error_count",
        "created_at",
        "created_by",
    )
    list_filter = ("status", "created_at")
    search_fields = ("filename",)
    readonly_fields = (
        "id",
        "filename",
        "status",
        "total_rows",
        "imported_count",
        "skipped_count",
        "error_count",
        "error_details",
        "started_at",
        "completed_at",
        "created_at",
        "created_by",
    )
    ordering = ("-created_at",)
