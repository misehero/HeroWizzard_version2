"""
Management command to apply category rules to uncategorized transactions.

Usage:
    python manage.py apply_rules
    python manage.py apply_rules --dry-run
    python manage.py apply_rules --all  # Re-apply to all transactions
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.transactions.models import Transaction
from apps.transactions.services import TransactionImporter


class Command(BaseCommand):
    help = "Apply auto-detection rules to transactions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without saving",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Apply rules to all transactions, not just uncategorized",
        )
        parser.add_argument(
            "--batch-id",
            type=str,
            help="Only process transactions from specific import batch",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        process_all = options["all"]
        batch_id = options.get("batch_id")

        # Build queryset
        qs = Transaction.objects.all()

        if batch_id:
            qs = qs.filter(import_batch_id=batch_id)
            self.stdout.write(f"Filtering to batch: {batch_id}")

        if not process_all:
            # Only uncategorized (missing P/V or druh)
            qs = qs.filter(Q(prijem_vydaj="") | Q(druh=""))
            self.stdout.write("Processing uncategorized transactions only")
        else:
            self.stdout.write(self.style.WARNING("Processing ALL transactions"))

        total = qs.count()
        self.stdout.write(f"Found {total} transactions to process")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No transactions to process"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        # Initialize importer (for rule matching logic)
        importer = TransactionImporter()
        importer._load_caches()

        updated_count = 0
        matched_rules = {}

        for txn in qs.iterator():
            original = {
                "prijem_vydaj": txn.prijem_vydaj,
                "druh": txn.druh,
                "detail": txn.detail,
                "kmen": txn.kmen,
            }

            # Apply rules
            txn = importer.apply_autodetection_rules(txn)

            # Check if anything changed
            changed = (
                txn.prijem_vydaj != original["prijem_vydaj"]
                or txn.druh != original["druh"]
                or txn.detail != original["detail"]
                or txn.kmen != original["kmen"]
            )

            if changed:
                updated_count += 1

                if not dry_run:
                    txn.save()

                # Track which rules matched (for reporting)
                rule_name = getattr(txn, "_matched_rule", "Unknown")
                matched_rules[rule_name] = matched_rules.get(rule_name, 0) + 1

                if updated_count <= 10:
                    self.stdout.write(
                        f"  Updated: {txn.datum} | {txn.castka} | "
                        f"{original['druh'] or '(empty)'} -> {txn.druh or '(empty)'}"
                    )

        if updated_count > 10:
            self.stdout.write(f"  ... and {updated_count - 10} more")

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would update {updated_count} of {total} transactions"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} of {total} transactions")
            )

        if matched_rules:
            self.stdout.write("\nRules matched:")
            for rule, count in sorted(matched_rules.items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {rule}: {count}")
