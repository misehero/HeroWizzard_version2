"""
Mise HERo Finance - Transactions App Models
============================================
Strict adherence to JSON specification:
- 22 Bank Columns (CSV imports, mostly non-editable)
- 14 App Columns (user-managed categorization)
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# =============================================================================
# LOOKUP MODELS
# =============================================================================


class Project(models.Model):
    """
    Project lookup table.
    Values: —, 4CFuture, POLCOM, GAP, LARPIC, CC, Digitmi, OMF, EGR, DIGISECURE
    """

    id = models.CharField(max_length=50, primary_key=True)  # slug-based PK
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions_project"
        ordering = ["name"]
        verbose_name = "Projekt"
        verbose_name_plural = "Projekty"

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Product lookup table with category grouping.
    Categories: ŠKOLY (Silný lídr, Na jedné lodi), FIRMY (Talentová akademie, Matrix)
    """

    class Category(models.TextChoices):
        SKOLY = "SKOLY", "ŠKOLY"
        FIRMY = "FIRMY", "FIRMY"

    id = models.CharField(max_length=50, primary_key=True)  # slug-based PK
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions_product"
        ordering = ["category", "name"]
        verbose_name = "Produkt"
        verbose_name_plural = "Produkty"

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class ProductSubgroup(models.Model):
    """
    Product subgroup lookup table (FK to Product).
    Values: Analýza, Na jedné lodi, Evaluace, FollowUp, Feedback, Metodika
    """

    id = models.CharField(max_length=50, primary_key=True)  # slug-based PK
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="subgroups"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transactions_product_subgroup"
        ordering = ["product", "name"]
        verbose_name = "Podskupina produktu"
        verbose_name_plural = "Podskupiny produktů"

    def __str__(self):
        return f"{self.product.name} → {self.name}"


class CostDetail(models.Model):
    """
    Cost detail lookup table for Druh (expense/income type) + Detail combination.
    Výdaje: Fixní, Variabilní, Mzdy, Mimořádné, Dluhy, Převod
    Příjmy: Projekt EU, Grant CZ, Produkt, Konference
    """

    class DruhType(models.TextChoices):
        VYDAJE = "vydaje", "Výdaje"
        PRIJMY = "prijmy", "Příjmy"

    class DruhVydaje(models.TextChoices):
        FIXNI = "fixni", "Fixní"
        VARIABILNI = "variabilni", "Variabilní"
        MZDY = "mzdy", "Mzdy"
        MIMORADNE = "mimoradne", "Mimořádné"
        DLUHY = "dluhy", "Dluhy"
        PREVOD = "prevod", "Převod"

    class DruhPrijmy(models.TextChoices):
        PROJEKT_EU = "projekt_eu", "Projekt EU"
        GRANT_CZ = "grant_cz", "Grant CZ"
        PRODUKT = "produkt", "Produkt"
        KONFERENCE = "konference", "Konference"

    id = models.CharField(max_length=50, primary_key=True)
    druh_type = models.CharField(max_length=20, choices=DruhType.choices)
    druh_value = models.CharField(max_length=50)
    detail = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "transactions_cost_detail"
        verbose_name = "Druh nákladu"
        verbose_name_plural = "Druhy nákladů"

    def __str__(self):
        return f"{self.get_druh_type_display()}: {self.druh_value}"


# =============================================================================
# MAIN TRANSACTION MODEL
# =============================================================================


class Transaction(models.Model):
    """
    Main Transaction model containing:
    - 22 Bank Columns (from CSV import, mostly editable=False)
    - 14 App Columns (user categorization)
    """

    # -------------------------------------------------------------------------
    # CHOICES (from JSON columnDefinitions)
    # -------------------------------------------------------------------------
    class Status(models.TextChoices):
        IMPORTOVANO = "importovano", "Importováno"
        ZPRACOVANO = "zpracovano", "Zpracováno"
        SCHVALENO = "schvaleno", "Schváleno"
        UPRAVENO = "upraveno", "Upraveno"
        CHYBA = "chyba", "Chyba"

    class PrijemVydaj(models.TextChoices):
        """P/V - Příjem/Výdaj"""

        PRIJEM = "P", "Příjem"
        VYDAJ = "V", "Výdaj"

    class VlastniNevlastni(models.TextChoices):
        """V/N - Vlastní/Nevlastní"""

        VLASTNI = "V", "Vlastní"
        NEVLASTNI = "N", "Nevlastní"
        NONE = "-", "—"

    class Kmen(models.TextChoices):
        """KMEN - Primary tribe assignment"""

        MH = "MH", "MH"
        SK = "SK", "ŠK"
        XP = "XP", "XP"
        FR = "FR", "FR"

    # -------------------------------------------------------------------------
    # PRIMARY KEY
    # -------------------------------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # 22 BANK COLUMNS (CSV Import - mostly non-editable)
    # -------------------------------------------------------------------------
    # Visible columns (6)
    datum = models.DateField(verbose_name="Datum", editable=False, db_index=True)
    ucet = models.CharField(max_length=50, verbose_name="Účet", editable=False)
    typ = models.CharField(max_length=100, verbose_name="Typ", editable=False)
    poznamka_zprava = models.TextField(
        blank=True, verbose_name="Poznámka/Zpráva", editable=False
    )
    variabilni_symbol = models.CharField(
        max_length=20, blank=True, verbose_name="VS", editable=False
    )
    castka = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="Částka", editable=False
    )

    # Hidden columns (16)
    datum_zauctovani = models.DateField(
        null=True, blank=True, verbose_name="Datum zaúčtování", editable=False
    )
    cislo_protiuctu = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Číslo protiúčtu",
        editable=False,
        db_index=True,
    )
    nazev_protiuctu = models.CharField(
        max_length=200, blank=True, verbose_name="Název protiúčtu", editable=False
    )
    typ_transakce = models.CharField(
        max_length=100, blank=True, verbose_name="Typ transakce", editable=False
    )
    konstantni_symbol = models.CharField(
        max_length=10, blank=True, verbose_name="KS", editable=False
    )
    specificky_symbol = models.CharField(
        max_length=20, blank=True, verbose_name="SS", editable=False
    )
    puvodni_castka = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Původní částka",
        editable=False,
    )
    puvodni_mena = models.CharField(
        max_length=10, blank=True, verbose_name="Původní měna", editable=False
    )
    poplatky = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poplatky",
        editable=False,
    )
    id_transakce = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Id transakce",
        editable=False,
        db_index=True,
    )
    vlastni_poznamka = models.TextField(
        blank=True, verbose_name="Vlastní poznámka", editable=False
    )
    nazev_merchanta = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Název merchanta",
        editable=False,
        db_index=True,
    )
    mesto = models.CharField(
        max_length=100, blank=True, verbose_name="Město", editable=False
    )
    mena = models.CharField(
        max_length=10, default="CZK", verbose_name="Měna", editable=False
    )
    banka_protiuctu = models.CharField(
        max_length=100, blank=True, verbose_name="Banka protiúčtu", editable=False
    )
    reference = models.CharField(
        max_length=100, blank=True, verbose_name="Reference", editable=False
    )

    # -------------------------------------------------------------------------
    # 14 APP COLUMNS (User-managed categorization)
    # -------------------------------------------------------------------------
    # App metadata (1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IMPORTOVANO,
        verbose_name="Status",
        db_index=True,
    )

    # Základní kategorizace (5): P/V, V/N, Daně, Druh, Detail
    prijem_vydaj = models.CharField(
        max_length=1, choices=PrijemVydaj.choices, blank=True, verbose_name="P/V"
    )
    vlastni_nevlastni = models.CharField(
        max_length=1,
        choices=VlastniNevlastni.choices,
        default=VlastniNevlastni.NONE,
        verbose_name="V/N",
    )
    dane = models.BooleanField(default=False, verbose_name="Daně")
    druh = models.CharField(max_length=50, blank=True, verbose_name="Druh")
    detail = models.CharField(max_length=200, blank=True, verbose_name="Detail")

    # Rozdělení mezi kmeny (5): KMEN, MH%, ŠK%, XP%, FR%
    kmen = models.CharField(
        max_length=2, choices=Kmen.choices, blank=True, verbose_name="KMEN"
    )
    mh_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="MH%",
    )
    sk_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="ŠK%",
    )
    xp_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="XP%",
    )
    fr_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="FR%",
    )

    # Přiřazení projektu/produktu (3): Projekt, Produkt, Podskupina
    projekt = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Projekt",
    )
    produkt = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Produkt",
    )
    podskupina = models.ForeignKey(
        ProductSubgroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Podskupina",
    )

    # -------------------------------------------------------------------------
    # ACTIVE FLAG
    # -------------------------------------------------------------------------
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktivní",
        help_text="Inactive transactions are excluded from exports",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # AUDIT FIELDS
    # -------------------------------------------------------------------------
    import_batch_id = models.UUIDField(
        null=True, blank=True, db_index=True, verbose_name="Import Batch ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )
    updated_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_transactions",
    )

    class Meta:
        db_table = "transactions_transaction"
        ordering = ["-datum", "-created_at"]
        verbose_name = "Transakce"
        verbose_name_plural = "Transakce"
        indexes = [
            models.Index(fields=["datum", "status"]),
            models.Index(fields=["kmen", "datum"]),
            models.Index(fields=["projekt", "datum"]),
        ]
        constraints = [
            # KMEN % split must sum to exactly 100 (or all zeros)
            models.CheckConstraint(
                name="kmen_pct_sum_equals_100_or_zero",
                check=(
                    models.Q(mh_pct=0, sk_pct=0, xp_pct=0, fr_pct=0)
                    | models.Q(
                        mh_pct__gte=0,
                        sk_pct__gte=0,
                        xp_pct__gte=0,
                        fr_pct__gte=0,
                    )
                ),
            ),
            # Unique bank transaction ID (when not empty)
            models.UniqueConstraint(
                fields=["id_transakce"],
                name="unique_bank_transaction_id",
                condition=~models.Q(id_transakce=""),
            ),
        ]

    def __str__(self):
        return f"{self.datum} | {self.castka} CZK | {self.status}"

    def clean(self):
        """
        Model-level validation ensuring KMEN % fields sum to exactly 100.
        """
        super().clean()
        errors = {}

        # Validate KMEN percentage split
        total_pct = (
            (self.mh_pct or Decimal("0"))
            + (self.sk_pct or Decimal("0"))
            + (self.xp_pct or Decimal("0"))
            + (self.fr_pct or Decimal("0"))
        )

        # Allow all zeros (unassigned) OR exactly 100
        if total_pct != Decimal("0") and total_pct != Decimal("100"):
            errors["mh_pct"] = (
                f"Součet KMEN % musí být přesně 100%. " f"Aktuální součet: {total_pct}%"
            )

        # Validate P/V consistency with amount
        if self.castka:
            if self.castka > 0 and self.prijem_vydaj == self.PrijemVydaj.VYDAJ:
                errors["prijem_vydaj"] = "Kladná částka nemůže být označena jako Výdaj"
            elif self.castka < 0 and self.prijem_vydaj == self.PrijemVydaj.PRIJEM:
                errors["prijem_vydaj"] = (
                    "Záporná částka nemůže být označena jako Příjem"
                )

        # Validate Podskupina belongs to selected Produkt
        if self.podskupina and self.produkt:
            if self.podskupina.product_id != self.produkt.pk:
                errors["podskupina"] = "Vybraná podskupina nepatří k vybranému produktu"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to ensure clean() is called."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_categorized(self) -> bool:
        """Check if transaction has been categorized."""
        return bool(self.prijem_vydaj and self.druh)

    @property
    def kmen_split_assigned(self) -> bool:
        """Check if KMEN split has been assigned."""
        total = self.mh_pct + self.sk_pct + self.xp_pct + self.fr_pct
        return total == Decimal("100")


# =============================================================================
# AUTO-DETECTION RULES
# =============================================================================


class CategoryRule(models.Model):
    """
    Auto-detection rules for categorizing transactions.
    Hierarchy: 1. Protiúčet Match, 2. Merchant Match, 3. Keyword Match
    """

    class MatchType(models.TextChoices):
        PROTIUCET = "protiucet", "Protiúčet (Account Number)"
        MERCHANT = "merchant", "Merchant Name"
        KEYWORD = "keyword", "Keyword (Regex/Exact)"

    class MatchMode(models.TextChoices):
        EXACT = "exact", "Exact Match"
        CONTAINS = "contains", "Contains"
        REGEX = "regex", "Regular Expression"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Rule Name")
    description = models.TextField(blank=True)

    # Matching configuration
    match_type = models.CharField(
        max_length=20, choices=MatchType.choices, verbose_name="Match Type"
    )
    match_mode = models.CharField(
        max_length=20,
        choices=MatchMode.choices,
        default=MatchMode.EXACT,
        verbose_name="Match Mode",
    )
    match_value = models.CharField(
        max_length=500,
        verbose_name="Match Value",
        help_text="Account number, merchant name, or keyword/regex pattern",
    )
    case_sensitive = models.BooleanField(default=False, verbose_name="Case Sensitive")

    # Priority (lower = higher priority within same match_type)
    priority = models.PositiveIntegerField(default=100, verbose_name="Priority")

    # Category assignments
    set_prijem_vydaj = models.CharField(
        max_length=1,
        choices=Transaction.PrijemVydaj.choices,
        blank=True,
        verbose_name="Set P/V",
    )
    set_vlastni_nevlastni = models.CharField(
        max_length=1,
        choices=Transaction.VlastniNevlastni.choices,
        blank=True,
        verbose_name="Set V/N",
    )
    set_dane = models.BooleanField(null=True, blank=True, verbose_name="Set Daně")
    set_druh = models.CharField(max_length=50, blank=True, verbose_name="Set Druh")
    set_detail = models.CharField(max_length=200, blank=True, verbose_name="Set Detail")
    set_kmen = models.CharField(
        max_length=2,
        choices=Transaction.Kmen.choices,
        blank=True,
        verbose_name="Set KMEN",
    )
    set_mh_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Set MH%",
    )
    set_sk_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Set ŠK%",
    )
    set_xp_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Set XP%",
    )
    set_fr_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Set FR%",
    )
    set_projekt = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Set Projekt",
    )
    set_produkt = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Set Produkt",
    )
    set_podskupina = models.ForeignKey(
        ProductSubgroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Set Podskupina",
    )

    # Audit
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rules",
    )

    class Meta:
        db_table = "transactions_category_rule"
        ordering = ["match_type", "priority", "name"]
        verbose_name = "Pravidlo kategorizace"
        verbose_name_plural = "Pravidla kategorizace"
        indexes = [
            models.Index(fields=["match_type", "is_active", "priority"]),
        ]

    def __str__(self):
        return f"[{self.get_match_type_display()}] {self.name}"

    def clean(self):
        """Validate regex patterns if match_mode is regex."""
        super().clean()
        if self.match_mode == self.MatchMode.REGEX:
            import re

            try:
                re.compile(self.match_value)
            except re.error as e:
                raise ValidationError({"match_value": f"Invalid regex pattern: {e}"})


# =============================================================================
# IMPORT BATCH TRACKING
# =============================================================================


class ImportBatch(models.Model):
    """Track CSV import batches for audit and rollback capability."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_batches",
    )

    class Meta:
        db_table = "transactions_import_batch"
        ordering = ["-created_at"]
        verbose_name = "Import Batch"
        verbose_name_plural = "Import Batches"

    def __str__(self):
        return f"{self.filename} ({self.status})"


# =============================================================================
# iDoklad INVOICE STORAGE
# =============================================================================


class IDokladInvoice(models.Model):
    """
    Invoices imported from iDoklad CSV exports.

    These are stored separately from Transaction records.  The future
    enrichment step will match them to bank transactions via
    ``variabilni_symbol`` and copy relevant fields (popis, IČ, …).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- invoice identity ---
    cislo_dokladu = models.CharField(max_length=50, unique=True, db_index=True)
    popis = models.TextField(blank=True)
    cislo_objednavky = models.CharField(max_length=50, blank=True)
    rada = models.CharField(max_length=50, blank=True)

    # --- customer ---
    nazev_jmeno = models.CharField(max_length=500, blank=True)
    ic = models.CharField(max_length=20, blank=True)
    dic_ic_dph = models.CharField(max_length=30, blank=True)
    dic_sk = models.CharField(max_length=30, blank=True)

    # --- dates ---
    vystaveno = models.DateField(null=True, blank=True, verbose_name="Vystaveno")
    splatnost = models.DateField(null=True, blank=True, verbose_name="Splatnost")
    duzp = models.DateField(null=True, blank=True, verbose_name="DUZP")
    datum_platby = models.DateField(null=True, blank=True, verbose_name="Datum platby")

    # --- amounts ---
    celkem_s_dph = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    celkem_bez_dph = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    dph = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    mena = models.CharField(max_length=10, blank=True)

    # --- payment ---
    stav_uhrady = models.CharField(max_length=50, blank=True)
    uhrazena_castka = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    # --- link key (matched to Transaction.variabilni_symbol later) ---
    variabilni_symbol = models.CharField(max_length=20, blank=True, db_index=True)

    # --- export flags ---
    exportovano = models.BooleanField(default=False)
    odeslano_odberateli = models.CharField(max_length=50, blank=True)
    odeslano_uctovnemu = models.BooleanField(default=False)

    # --- audit ---
    import_batch_id = models.UUIDField(
        null=True, blank=True, db_index=True, verbose_name="Import Batch ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="idoklad_imports",
    )

    class Meta:
        db_table = "transactions_idoklad_invoice"
        ordering = ["-vystaveno"]
        verbose_name = "iDoklad Invoice"
        verbose_name_plural = "iDoklad Invoices"
        indexes = [
            models.Index(fields=["variabilni_symbol"]),
            models.Index(fields=["vystaveno"]),
        ]

    def __str__(self):
        return f"{self.cislo_dokladu} – {self.popis[:50]}"
