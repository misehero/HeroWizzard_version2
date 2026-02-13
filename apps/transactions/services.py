"""
Mise HERo Finance - Transactions Import Service
================================================
Handles CSV import with auto-detection rule application.
"""

import csv
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any, BinaryIO, Optional, TextIO

from django.db import transaction as db_transaction
from django.utils import timezone

from .models import (CategoryRule, ImportBatch, Product, Project, Transaction,
                     TransactionAuditLog)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ImportResult:
    """Result of a single row import attempt."""

    success: bool
    row_number: int
    transaction_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportSummary:
    """Summary of entire import batch."""

    batch_id: uuid.UUID
    total_rows: int
    imported: int
    skipped: int
    errors: int
    error_details: list[dict]
    duration_seconds: float


# =============================================================================
# CSV COLUMN MAPPINGS
# =============================================================================

# Generic Czech bank CSV format
GENERIC_CSV_MAPPING = {
    # Visible columns (6)
    "Datum": "datum",
    "Účet": "ucet",
    "Typ": "typ",
    "Poznámka/Zpráva": "poznamka_zprava",
    "Poznámka/zpráva": "poznamka_zprava",
    "VS": "variabilni_symbol",
    "Variabilní symbol": "variabilni_symbol",
    "Částka": "castka",
    # Hidden columns (16)
    "Datum zaúčtování": "datum_zauctovani",
    "Číslo protiúčtu": "cislo_protiuctu",
    "Název protiúčtu": "nazev_protiuctu",
    "Typ transakce": "typ_transakce",
    "KS": "konstantni_symbol",
    "Konstantní symbol": "konstantni_symbol",
    "SS": "specificky_symbol",
    "Specifický symbol": "specificky_symbol",
    "Původní částka": "puvodni_castka",
    "Původní měna": "puvodni_mena",
    "Poplatky": "poplatky",
    "Id transakce": "id_transakce",
    "ID transakce": "id_transakce",
    "Vlastní poznámka": "vlastni_poznamka",
    "Název merchanta": "nazev_merchanta",
    "Město": "mesto",
    "Měna": "mena",
    "Banka protiúčtu": "banka_protiuctu",
    "Reference": "reference",
}

# Raiffeisen Bank Czech CSV format
# Note: "Původní částka a měna" appears twice (amount + currency) - handled specially
RAIFFEISEN_CSV_MAPPING = {
    # Date fields
    "Datum provedení": "datum",
    "Datum zaúčtování": "datum_zauctovani",
    # Account info
    "Číslo účtu": "ucet",
    "Název účtu": "_skip",  # Not in Transaction model
    "Kategorie transakce": "typ",
    # Counterparty
    "Číslo protiúčtu": "cislo_protiuctu",
    "Název protiúčtu": "nazev_protiuctu",
    # Transaction details
    "Typ transakce": "typ_transakce",
    "Zpráva": "poznamka_zprava",
    "Poznámka": "vlastni_poznamka",
    # Symbols
    "VS": "variabilni_symbol",
    "KS": "konstantni_symbol",
    "SS": "specificky_symbol",
    # Amounts
    "Zaúčtovaná částka": "castka",
    "Měna účtu": "mena",
    # Fees
    "Poplatek": "poplatky",
    # IDs
    "Id transakce": "id_transakce",
    # Other
    "Vlastní poznámka": "_vlastni_poznamka_override",
    "Název obchodníka": "nazev_merchanta",
    "Město": "mesto",
}

# Creditas Bank Czech CSV format
# Structure: rows 0-2 are an account metadata block; row 3 is the real header row.
# Account number and bank code are in separate columns — joined in the parser.
# "Datum provedení" is consistently empty; parser falls back to "Datum zaúčtování".
CREDITAS_CSV_MAPPING = {
    "Můj účet": "_ucet",                    # joined with bank code → ucet
    "Můj účet-banka": "_ucet_banka",        # bank code half of ucet
    "Název mého účtu": "_skip",
    "Datum zaúčtování": "datum_zauctovani",
    "Datum provedení": "datum",             # often empty; fallback applied in parser
    "Protiúčet": "_protiucet",              # joined with bank code → cislo_protiuctu
    "Protiúčet-banka": "_protiucet_banka",  # also stored as banka_protiuctu
    "Název protiúčtu": "nazev_protiuctu",
    "Kód transakce": "typ",
    "VS": "variabilni_symbol",
    "SS": "specificky_symbol",
    "KS": "konstantni_symbol",
    "E2E": "reference",
    "Zpráva pro protistranu": "poznamka_zprava",
    "Poznámka": "vlastni_poznamka",
    "Platba/Vklad": "_skip",                # redundant with sign of Částka
    "Částka": "castka",
    "Měna": "mena",
    "Kategorie": "_skip",                   # bank's own label; ignored
}

# First-row (metadata block) headers that identify a Creditas export
CREDITAS_SIGNATURE_HEADERS = {"Typ účtu", "IBAN", "BIC"}

# Headers to skip in mapping (they don't map to model fields)
SKIP_FIELDS = {"_skip", "_vlastni_poznamka_override"}

# Raiffeisen unique headers for detection
RAIFFEISEN_SIGNATURE_HEADERS = {"Datum provedení", "Zaúčtovaná částka", "Název obchodníka"}

# Backward compatibility alias
CSV_COLUMN_MAPPING = GENERIC_CSV_MAPPING


# =============================================================================
# TRANSACTION IMPORTER SERVICE
# =============================================================================


class TransactionImporter:
    """
    Service class for importing bank transactions from CSV files.

    Features:
    - CSV parsing with Czech column header support
    - Duplicate detection via id_transakce
    - Auto-detection rules application with hierarchy:
      1. Protiúčet (counterparty account) match
      2. Merchant name match
      3. Keyword (regex/exact) match
    - Batch tracking for audit and rollback
    """

    def __init__(self, user=None):
        """
        Initialize the importer.

        Args:
            user: The user performing the import (for audit trail)
        """
        self.user = user
        self._rules_cache: Optional[dict] = None
        self._projects_cache: Optional[dict] = None
        self._products_cache: Optional[dict] = None

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def import_csv(
        self,
        file_stream: BinaryIO | TextIO,
        filename: str = "unknown.csv",
        encoding: str = "utf-8-sig",  # Handle BOM
        delimiter: str = ";",  # Czech CSVs often use semicolon
    ) -> ImportSummary:
        """
        Import transactions from a CSV file stream.

        Args:
            file_stream: File-like object containing CSV data
            filename: Original filename for batch tracking
            encoding: CSV file encoding
            delimiter: CSV field delimiter

        Returns:
            ImportSummary with results of the import operation
        """
        start_time = timezone.now()

        # Create import batch record
        batch = ImportBatch.objects.create(
            filename=filename,
            status=ImportBatch.Status.PROCESSING,
            started_at=start_time,
            created_by=self.user,
        )

        results: list[ImportResult] = []

        try:
            # Parse CSV and process rows
            rows = self.parse_csv(file_stream, encoding, delimiter)
            batch.total_rows = len(rows)
            batch.save(update_fields=["total_rows"])

            # Load rules and lookup caches
            self._load_caches()

            # Process each row within a transaction
            with db_transaction.atomic():
                for row_num, row_data in enumerate(rows, start=1):
                    result = self._process_row(row_num, row_data, batch.id)
                    results.append(result)

            # Update batch with results
            batch.imported_count = sum(1 for r in results if r.success)
            batch.skipped_count = sum(
                1
                for r in results
                if not r.success and "duplicate" in (r.error_message or "").lower()
            )
            batch.error_count = sum(
                1
                for r in results
                if not r.success and "duplicate" not in (r.error_message or "").lower()
            )
            batch.error_details = [
                {"row": r.row_number, "error": r.error_message}
                for r in results
                if not r.success
            ]
            batch.status = ImportBatch.Status.COMPLETED
            batch.completed_at = timezone.now()
            batch.save()

        except Exception as e:
            logger.exception(f"Import failed for batch {batch.id}")
            batch.status = ImportBatch.Status.FAILED
            batch.error_details = [{"error": str(e)}]
            batch.completed_at = timezone.now()
            batch.save()
            raise

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return ImportSummary(
            batch_id=batch.id,
            total_rows=batch.total_rows,
            imported=batch.imported_count,
            skipped=batch.skipped_count,
            errors=batch.error_count,
            error_details=batch.error_details,
            duration_seconds=duration,
        )

    def detect_csv_format(self, headers: list[str]) -> str:
        """
        Detect CSV format based on headers.

        Args:
            headers: List of CSV column headers (first row of the file)

        Returns:
            Format identifier: 'creditas', 'raiffeisen', or 'generic'
        """
        headers_set = set(headers)

        # Creditas exports start with an account-metadata block; row 0 contains
        # these signature headers rather than transaction columns.
        if CREDITAS_SIGNATURE_HEADERS.issubset(headers_set):
            logger.info("Detected Creditas Bank CSV format")
            return "creditas"

        # Check for Raiffeisen-specific headers
        if RAIFFEISEN_SIGNATURE_HEADERS.intersection(headers_set):
            logger.info("Detected Raiffeisen Bank CSV format")
            return "raiffeisen"

        logger.info("Using generic CSV format")
        return "generic"

    def parse_csv(
        self,
        file_stream: BinaryIO | TextIO,
        encoding: str = "utf-8-sig",
        delimiter: str = ";",
    ) -> list[dict[str, Any]]:
        """
        Parse CSV file and return list of row dictionaries.
        Auto-detects bank format (Raiffeisen vs generic).

        Args:
            file_stream: File-like object containing CSV data
            encoding: CSV file encoding
            delimiter: CSV field delimiter

        Returns:
            List of dictionaries mapping CSV headers to values
        """
        # Convert binary stream to text if needed
        if hasattr(file_stream, "read"):
            content = file_stream.read()
            if isinstance(content, bytes):
                # Czech bank exports are often cp1250; fall back if utf-8-sig fails
                for enc in (encoding, "cp1250"):
                    try:
                        content = content.decode(enc)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    raise ValueError(
                        f"Unable to decode CSV. Tried: {encoding}, cp1250"
                    )
        else:
            content = str(file_stream)

        # Use csv.reader for positional access (needed for Raiffeisen duplicate headers)
        reader = csv.reader(StringIO(content), delimiter=delimiter)
        all_rows = list(reader)

        if not all_rows:
            return []

        # Get headers (first row)
        headers = all_rows[0]
        csv_format = self.detect_csv_format(headers)

        # Select appropriate mapping
        if csv_format == "creditas":
            return self._parse_creditas_csv(all_rows)
        elif csv_format == "raiffeisen":
            return self._parse_raiffeisen_csv(headers, all_rows[1:])
        else:
            return self._parse_generic_csv(headers, all_rows[1:])

    def _parse_generic_csv(
        self, headers: list[str], data_rows: list[list[str]]
    ) -> list[dict[str, Any]]:
        """Parse generic bank CSV format."""
        rows = []
        for row in data_rows:
            if not any(cell.strip() for cell in row):
                continue  # Skip empty rows

            mapped_row = {}
            for idx, header in enumerate(headers):
                if idx >= len(row):
                    continue
                value = row[idx]
                model_field = GENERIC_CSV_MAPPING.get(header)
                if model_field and model_field not in SKIP_FIELDS:
                    mapped_row[model_field] = value

            if mapped_row:
                rows.append(mapped_row)

        return rows

    def _parse_raiffeisen_csv(
        self, headers: list[str], data_rows: list[list[str]]
    ) -> list[dict[str, Any]]:
        """
        Parse Raiffeisen Bank CSV format.
        Handles duplicate "Původní částka a měna" columns (amount + currency).
        """
        # Find indices for special handling
        puvodni_indices = []
        for idx, header in enumerate(headers):
            if header == "Původní částka a měna":
                puvodni_indices.append(idx)

        rows = []
        for row in data_rows:
            if not any(cell.strip() for cell in row):
                continue  # Skip empty rows

            mapped_row = {}
            vlastni_poznamka_value = None

            for idx, header in enumerate(headers):
                if idx >= len(row):
                    continue
                value = row[idx]

                # Handle duplicate "Původní částka a měna" columns
                if header == "Původní částka a měna":
                    if len(puvodni_indices) >= 2:
                        # First occurrence is amount, second is currency
                        if idx == puvodni_indices[0]:
                            mapped_row["puvodni_castka"] = value
                        elif idx == puvodni_indices[1]:
                            mapped_row["puvodni_mena"] = value
                    continue

                model_field = RAIFFEISEN_CSV_MAPPING.get(header)
                if not model_field:
                    continue

                # Handle skipped fields
                if model_field == "_skip":
                    continue

                # Handle Vlastní poznámka override
                if model_field == "_vlastni_poznamka_override":
                    vlastni_poznamka_value = value
                    continue

                mapped_row[model_field] = value

            # Apply Vlastní poznámka if not already set by Poznámka
            if vlastni_poznamka_value and not mapped_row.get("vlastni_poznamka"):
                mapped_row["vlastni_poznamka"] = vlastni_poznamka_value

            if mapped_row:
                rows.append(mapped_row)

        return rows

    def _parse_creditas_csv(self, all_rows: list[list[str]]) -> list[dict[str, Any]]:
        """
        Parse Creditas Bank CSV format.

        The file begins with a 3-row account-metadata block:
            Row 0 – metadata column headers (Typ účtu, IBAN, …)
            Row 1 – metadata values
            Row 2 – empty separator
        Transaction column headers follow on the next non-empty row.

        Post-processing per row:
        - Account + bank-code columns are joined into "account/bank" format.
        - If "Datum provedení" is empty, "Datum zaúčtování" is used as fallback
          for the required ``datum`` field.
        """
        # Locate the transaction header row by scanning for known Creditas columns
        header_row_idx: Optional[int] = None
        for idx, row in enumerate(all_rows[:10]):
            if "Částka" in row and "Protiúčet" in row and "Platba/Vklad" in row:
                header_row_idx = idx
                break

        if header_row_idx is None:
            raise ValueError(
                "Nelze najít řádek s hlavičkami transakcí v CSV souboru Creditas"
            )

        headers = all_rows[header_row_idx]
        data_rows = all_rows[header_row_idx + 1:]

        rows: list[dict[str, Any]] = []
        for row in data_rows:
            if not any(cell.strip() for cell in row):
                continue  # skip empty rows

            mapped_row: dict[str, Any] = {}
            internal: dict[str, str] = {}  # staging for fields that need post-processing

            for idx, header in enumerate(headers):
                if idx >= len(row):
                    continue
                value = row[idx].strip()

                model_field = CREDITAS_CSV_MAPPING.get(header)
                if not model_field:
                    continue
                if model_field == "_skip":
                    continue

                # Fields starting with '_' need post-processing (account joining)
                if model_field.startswith("_"):
                    internal[model_field] = value
                    continue

                mapped_row[model_field] = value

            # --- post-processing ---

            # Join account number + bank code into "account/bank" format
            ucet = internal.get("_ucet", "")
            ucet_banka = internal.get("_ucet_banka", "")
            mapped_row["ucet"] = f"{ucet}/{ucet_banka}" if ucet and ucet_banka else ucet

            protiucet = internal.get("_protiucet", "")
            protiucet_banka = internal.get("_protiucet_banka", "")
            if protiucet:
                mapped_row["cislo_protiuctu"] = (
                    f"{protiucet}/{protiucet_banka}" if protiucet_banka else protiucet
                )
            if protiucet_banka:
                mapped_row["banka_protiuctu"] = protiucet_banka

            # Datum fallback: "Datum provedení" is empty in Creditas exports
            if not mapped_row.get("datum") and mapped_row.get("datum_zauctovani"):
                mapped_row["datum"] = mapped_row["datum_zauctovani"]

            if mapped_row:
                rows.append(mapped_row)

        return rows

    def apply_autodetection_rules(self, transaction: Transaction) -> Transaction:
        """
        Apply auto-detection rules to categorize a transaction.

        Hierarchy (first match wins within each level):
        1. Protiúčet Match - Match by counterparty account number
        2. Merchant Match - Match by merchant name
        3. Keyword Match - Match by regex/exact keyword in message/notes

        Args:
            transaction: Transaction instance to categorize

        Returns:
            Transaction with applied categorization (not yet saved)
        """
        if self._rules_cache is None:
            self._load_caches()

        # Try each match type in hierarchy order
        matched_rule: Optional[CategoryRule] = None

        # 1. Protiúčet (Account Number) Match - Highest Priority
        if transaction.cislo_protiuctu:
            matched_rule = self._find_matching_rule(
                CategoryRule.MatchType.PROTIUCET,
                transaction.cislo_protiuctu,
            )

        # 2. Merchant Name Match
        if matched_rule is None and transaction.nazev_merchanta:
            matched_rule = self._find_matching_rule(
                CategoryRule.MatchType.MERCHANT,
                transaction.nazev_merchanta,
            )

        # 3. Keyword Match (check multiple fields)
        if matched_rule is None:
            search_text = " ".join(
                filter(
                    None,
                    [
                        transaction.poznamka_zprava,
                        transaction.vlastni_poznamka,
                        transaction.nazev_protiuctu,
                    ],
                )
            )
            if search_text:
                matched_rule = self._find_matching_rule(
                    CategoryRule.MatchType.KEYWORD,
                    search_text,
                )

        # Apply matched rule
        if matched_rule:
            self._apply_rule_to_transaction(matched_rule, transaction)

        return transaction

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    def _load_caches(self) -> None:
        """Load rules and lookup tables into memory for performance."""
        # Load active rules ordered by type and priority
        rules = CategoryRule.objects.filter(is_active=True).order_by(
            "match_type", "priority"
        )

        self._rules_cache = {
            CategoryRule.MatchType.PROTIUCET: [],
            CategoryRule.MatchType.MERCHANT: [],
            CategoryRule.MatchType.KEYWORD: [],
        }

        for rule in rules:
            self._rules_cache[rule.match_type].append(rule)

        # Cache lookups
        self._projects_cache = {p.id: p for p in Project.objects.filter(is_active=True)}
        self._products_cache = {p.id: p for p in Product.objects.filter(is_active=True)}

    def _process_row(
        self,
        row_number: int,
        row_data: dict[str, Any],
        batch_id: uuid.UUID,
    ) -> ImportResult:
        """
        Process a single CSV row into a Transaction.

        Args:
            row_number: Row number for error reporting
            row_data: Dictionary of field values
            batch_id: Import batch ID

        Returns:
            ImportResult indicating success or failure
        """
        try:
            # Check for duplicate
            id_transakce = row_data.get("id_transakce", "").strip()
            if id_transakce:
                if Transaction.objects.filter(id_transakce=id_transakce).exists():
                    return ImportResult(
                        success=False,
                        row_number=row_number,
                        error_message=f"Duplicate transaction ID: {id_transakce}",
                    )

            # Convert and validate data
            transaction_data = self._convert_row_data(row_data)
            transaction_data["import_batch_id"] = batch_id
            transaction_data["created_by"] = self.user
            transaction_data["updated_by"] = self.user

            # Create transaction instance (not saved yet)
            transaction = Transaction(**transaction_data)

            # Apply auto-detection rules
            transaction = self.apply_autodetection_rules(transaction)

            # Auto-determine P/V from amount
            if not transaction.prijem_vydaj and transaction.castka:
                transaction.prijem_vydaj = (
                    Transaction.PrijemVydaj.PRIJEM
                    if transaction.castka > 0
                    else Transaction.PrijemVydaj.VYDAJ
                )

            # Save transaction
            transaction.save()

            # Audit log
            TransactionAuditLog.objects.create(
                transaction=transaction,
                user=self.user,
                action="Import z CSV",
                details=f"Soubor: batch {batch_id}",
            )

            return ImportResult(
                success=True,
                row_number=row_number,
                transaction_id=transaction.id,
            )

        except Exception as e:
            logger.warning(f"Failed to import row {row_number}: {e}")
            return ImportResult(
                success=False,
                row_number=row_number,
                error_message=str(e),
            )

    def _convert_row_data(self, row_data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert raw CSV string values to appropriate Python types.

        Args:
            row_data: Dictionary of string values from CSV

        Returns:
            Dictionary with converted types
        """
        converted = {}

        for field_name, value in row_data.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            value = str(value).strip()

            # Date fields
            if field_name in ("datum", "datum_zauctovani"):
                converted[field_name] = self._parse_date(value)

            # Decimal fields
            elif field_name in ("castka", "puvodni_castka", "poplatky"):
                converted[field_name] = self._parse_decimal(value)

            # String fields
            else:
                converted[field_name] = value

        return converted

    def _parse_date(self, value: str) -> Optional[datetime]:
        """
        Parse date/datetime string in various formats.

        Supports:
        - DD.MM.YYYY (Czech standard)
        - DD.MM.YYYY HH:MM (Raiffeisen Bank datetime format)
        - DD/MM/YYYY
        - YYYY-MM-DD (ISO format)
        """
        # Date formats (most common first)
        date_formats = [
            "%d.%m.%Y %H:%M",  # Raiffeisen datetime: 16.08.2025 05:42
            "%d.%m.%Y",        # Czech date: 14.08.2025
            "%d/%m/%Y",        # Alternative: 14/08/2025
            "%Y-%m-%d",        # ISO: 2025-08-14
            "%Y-%m-%d %H:%M:%S",  # ISO datetime
        ]

        for fmt in date_formats:
            try:
                parsed = datetime.strptime(value.strip(), fmt)
                # Return just the date part for consistency
                return parsed.date()
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date: {value}")

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse decimal string, handling Czech number format."""
        # Czech format: 1 234,56 (space as thousand separator, comma as decimal)
        try:
            # Remove spaces (thousand separators)
            cleaned = value.replace(" ", "").replace("\xa0", "")
            # Replace comma with period for decimal
            cleaned = cleaned.replace(",", ".")
            return Decimal(cleaned)
        except InvalidOperation:
            raise ValueError(f"Unable to parse decimal: {value}")

    def _find_matching_rule(
        self,
        match_type: str,
        search_value: str,
    ) -> Optional[CategoryRule]:
        """
        Find first matching rule for given type and value.

        Args:
            match_type: CategoryRule.MatchType value
            search_value: String to match against

        Returns:
            First matching CategoryRule or None
        """
        rules = self._rules_cache.get(match_type, [])

        for rule in rules:
            if self._rule_matches(rule, search_value):
                return rule

        return None

    def _rule_matches(self, rule: CategoryRule, search_value: str) -> bool:
        """
        Check if a rule matches the given search value.

        Args:
            rule: CategoryRule to check
            search_value: String to match against

        Returns:
            True if rule matches
        """
        pattern = rule.match_value
        target = search_value

        if not rule.case_sensitive:
            pattern = pattern.lower()
            target = target.lower()

        if rule.match_mode == CategoryRule.MatchMode.EXACT:
            return pattern == target

        elif rule.match_mode == CategoryRule.MatchMode.CONTAINS:
            return pattern in target

        elif rule.match_mode == CategoryRule.MatchMode.REGEX:
            try:
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                return bool(re.search(rule.match_value, search_value, flags))
            except re.error:
                logger.warning(f"Invalid regex in rule {rule.id}: {rule.match_value}")
                return False

        return False

    def _apply_rule_to_transaction(
        self,
        rule: CategoryRule,
        transaction: Transaction,
    ) -> None:
        """
        Apply rule settings to transaction.

        Args:
            rule: CategoryRule with settings to apply
            transaction: Transaction to modify
        """
        # Only set values if rule has them defined
        if rule.set_prijem_vydaj:
            transaction.prijem_vydaj = rule.set_prijem_vydaj

        if rule.set_vlastni_nevlastni:
            transaction.vlastni_nevlastni = rule.set_vlastni_nevlastni

        if rule.set_dane is not None:
            transaction.dane = rule.set_dane

        if rule.set_druh:
            transaction.druh = rule.set_druh

        if rule.set_detail:
            transaction.detail = rule.set_detail

        if rule.set_kmen:
            transaction.kmen = rule.set_kmen

        if rule.set_mh_pct is not None:
            transaction.mh_pct = rule.set_mh_pct

        if rule.set_sk_pct is not None:
            transaction.sk_pct = rule.set_sk_pct

        if rule.set_xp_pct is not None:
            transaction.xp_pct = rule.set_xp_pct

        if rule.set_fr_pct is not None:
            transaction.fr_pct = rule.set_fr_pct

        if rule.set_projekt_id:
            transaction.projekt_id = rule.set_projekt_id

        if rule.set_produkt_id:
            transaction.produkt_id = rule.set_produkt_id

        if rule.set_podskupina_id:
            transaction.podskupina_id = rule.set_podskupina_id


# =============================================================================
# iDoklad INVOICE IMPORTER
# =============================================================================

# iDoklad CSV column → IDokladInvoice model field
IDOKLAD_CSV_MAPPING = {
    "Číslo dokladu": "cislo_dokladu",
    "Popis": "popis",
    "Číslo objednávky": "cislo_objednavky",
    "Řada": "rada",
    "Název/Jméno": "nazev_jmeno",
    "IČ": "ic",
    "DIČ / IČ DPH": "dic_ic_dph",
    "DIČ (SK)": "dic_sk",
    "Vystaveno": "vystaveno",
    "Splatnost": "splatnost",
    "DUZP": "duzp",
    "Datum platby": "datum_platby",
    "Celkem s DPH": "celkem_s_dph",
    "Celkem bez DPH": "celkem_bez_dph",
    "DPH": "dph",
    "Měna": "mena",
    "Stav úhrady": "stav_uhrady",
    "Uhrazená částka": "uhrazena_castka",
    "Variabilní symbol": "variabilni_symbol",
    "Exportováno": "exportovano",
    "Odesláno odběrateli": "odeslano_odberateli",
    "Odesláno účetnímu": "odeslano_uctovnemu",
}

# Fields that hold a date value
_IDOKLAD_DATE_FIELDS = {"vystaveno", "splatnost", "duzp", "datum_platby"}

# Fields that hold a decimal value
_IDOKLAD_DECIMAL_FIELDS = {
    "celkem_s_dph", "celkem_bez_dph", "dph", "uhrazena_castka"
}

# Fields that are boolean (Ano/Ne)
_IDOKLAD_BOOL_FIELDS = {"exportovano", "odeslano_uctovnemu"}


class IDokladImporter:
    """
    Import invoices from iDoklad CSV exports into IDokladInvoice.

    Format notes:
    - Delimiter: comma
    - Encoding: UTF-8 with BOM
    - Dates: MM/DD/YYYY (US locale used by iDoklad)
    - Amounts: period decimal separator, no thousand separator
    - Booleans: "Ano" / "Ne"

    Deduplication is by ``cislo_dokladu`` (unique across all imports).
    """

    def __init__(self, user=None):
        self.user = user

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------

    def import_csv(
        self,
        file_stream: BinaryIO | TextIO,
        filename: str = "unknown.csv",
    ) -> ImportSummary:
        """Parse and persist iDoklad invoices; return a summary."""
        from .models import IDokladInvoice, ImportBatch

        start_time = timezone.now()

        batch = ImportBatch.objects.create(
            filename=filename,
            status=ImportBatch.Status.PROCESSING,
            started_at=start_time,
            created_by=self.user,
        )

        imported = skipped = errors = 0
        error_details: list[dict] = []

        try:
            rows = self._parse_csv(file_stream)
            batch.total_rows = len(rows)

            with db_transaction.atomic():
                for row_num, row in enumerate(rows, start=1):
                    try:
                        cislo = row.get("Číslo dokladu", "").strip()
                        if not cislo:
                            raise ValueError("Chybí Číslo dokladu")

                        if IDokladInvoice.objects.filter(cislo_dokladu=cislo).exists():
                            skipped += 1
                            continue

                        invoice_data = self._convert_row(row)
                        invoice_data["import_batch_id"] = batch.id
                        invoice_data["created_by"] = self.user

                        IDokladInvoice.objects.create(**invoice_data)
                        imported += 1

                    except Exception as e:
                        logger.warning(f"iDoklad row {row_num} failed: {e}")
                        errors += 1
                        error_details.append({"row": row_num, "error": str(e)})

            batch.imported_count = imported
            batch.skipped_count = skipped
            batch.error_count = errors
            batch.error_details = error_details
            batch.status = ImportBatch.Status.COMPLETED
            batch.completed_at = timezone.now()
            batch.save()

        except Exception as e:
            logger.exception(f"iDoklad import failed for batch {batch.id}")
            batch.status = ImportBatch.Status.FAILED
            batch.error_details = [{"error": str(e)}]
            batch.completed_at = timezone.now()
            batch.save()
            raise

        duration = (timezone.now() - start_time).total_seconds()

        return ImportSummary(
            batch_id=batch.id,
            total_rows=batch.total_rows,
            imported=imported,
            skipped=skipped,
            errors=errors,
            error_details=error_details,
            duration_seconds=duration,
        )

    # -------------------------------------------------------------------------
    # PRIVATE
    # -------------------------------------------------------------------------

    def _parse_csv(self, file_stream: BinaryIO | TextIO) -> list[dict[str, str]]:
        """Read iDoklad CSV (comma-delimited, UTF-8 BOM)."""
        if hasattr(file_stream, "read"):
            content = file_stream.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig")
        else:
            content = str(file_stream)

        reader = csv.DictReader(StringIO(content), delimiter=",")
        return list(reader)

    def _convert_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Map CSV columns to model fields and convert types."""
        converted: dict[str, Any] = {}

        for csv_header, model_field in IDOKLAD_CSV_MAPPING.items():
            value = row.get(csv_header, "").strip()
            if not value:
                continue

            if model_field in _IDOKLAD_DATE_FIELDS:
                converted[model_field] = self._parse_date(value)
            elif model_field in _IDOKLAD_DECIMAL_FIELDS:
                converted[model_field] = Decimal(value)
            elif model_field in _IDOKLAD_BOOL_FIELDS:
                converted[model_field] = value.lower() in ("ano", "yes", "true", "1")
            else:
                converted[model_field] = value

        return converted

    @staticmethod
    def _parse_date(value: str):
        """Parse date — iDoklad exports MM/DD/YYYY; also accept DD.MM.YYYY."""
        for fmt in ("%m/%d/%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {value}")
