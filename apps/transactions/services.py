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

from .models import CategoryRule, ImportBatch, Product, Project, Transaction

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
# CSV COLUMN MAPPING
# =============================================================================

# Maps Czech CSV headers to Transaction model fields (22 Bank Columns)
CSV_COLUMN_MAPPING = {
    # Visible columns (6)
    "Datum": "datum",
    "Účet": "ucet",
    "Typ": "typ",
    "Poznámka/Zpráva": "poznamka_zprava",
    "VS": "variabilni_symbol",
    "Částka": "castka",
    # Hidden columns (16)
    "Datum zaúčtování": "datum_zauctovani",
    "Číslo protiúčtu": "cislo_protiuctu",
    "Název protiúčtu": "nazev_protiuctu",
    "Typ transakce": "typ_transakce",
    "KS": "konstantni_symbol",
    "SS": "specificky_symbol",
    "Původní částka": "puvodni_castka",
    "Původní měna": "puvodni_mena",
    "Poplatky": "poplatky",
    "Id transakce": "id_transakce",
    "Vlastní poznámka": "vlastni_poznamka",
    "Název merchanta": "nazev_merchanta",
    "Město": "mesto",
    "Měna": "mena",
    "Banka protiúčtu": "banka_protiuctu",
    "Reference": "reference",
}


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

    def parse_csv(
        self,
        file_stream: BinaryIO | TextIO,
        encoding: str = "utf-8-sig",
        delimiter: str = ";",
    ) -> list[dict[str, Any]]:
        """
        Parse CSV file and return list of row dictionaries.

        Args:
            file_stream: File-like object containing CSV data
            encoding: CSV file encoding
            delimiter: CSV field delimiter

        Returns:
            List of dictionaries mapping CSV headers to values
        """
        # TODO: Implement full CSV parsing logic
        # Handle:
        # - BOM detection
        # - Header row detection
        # - Empty row skipping
        # - Data type conversion (dates, decimals)

        # Convert binary stream to text if needed
        if hasattr(file_stream, "read"):
            content = file_stream.read()
            if isinstance(content, bytes):
                content = content.decode(encoding)
        else:
            content = str(file_stream)

        # Parse CSV
        reader = csv.DictReader(
            StringIO(content),
            delimiter=delimiter,
        )

        rows = []
        for row in reader:
            # Map Czech headers to model field names
            mapped_row = {}
            for csv_header, model_field in CSV_COLUMN_MAPPING.items():
                if csv_header in row:
                    mapped_row[model_field] = row[csv_header]

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
        """Parse date string in various formats."""
        # TODO: Support multiple date formats
        # Common Czech formats: DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD
        formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
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
