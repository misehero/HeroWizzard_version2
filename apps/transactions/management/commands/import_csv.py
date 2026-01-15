"""
Management command to import transactions from CSV file.

Usage:
    python manage.py import_csv path/to/file.csv
    python manage.py import_csv path/to/file.csv --dry-run
    python manage.py import_csv path/to/file.csv --no-rules
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.transactions.services import TransactionImporter

User = get_user_model()


class Command(BaseCommand):
    help = "Import transactions from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the CSV file to import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse file without saving to database",
        )
        parser.add_argument(
            "--no-rules",
            action="store_true",
            help="Skip auto-detection rules",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Email of user to attribute import to",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        dry_run = options["dry_run"]
        _apply_rules = not options["no_rules"]  # noqa: F841 TODO: pass to importer

        # Get user if specified
        user = None
        if options["user"]:
            try:
                user = User.objects.get(email=options["user"])
            except User.DoesNotExist:
                raise CommandError(f"User with email '{options['user']}' not found")

        self.stdout.write(f"Importing from: {csv_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no data will be saved"))

        try:
            with open(csv_path, "rb") as f:
                importer = TransactionImporter(user=user)

                if dry_run:
                    # Just parse and report
                    rows = importer.parse_csv(f)
                    self.stdout.write(f"Parsed {len(rows)} rows")

                    # Show first few rows
                    for i, row in enumerate(rows[:5]):
                        self.stdout.write(
                            f"  Row {i+1}: {row.get('datum')} | {row.get('castka')} | {row.get('poznamka_zprava', '')[:50]}"
                        )

                    if len(rows) > 5:
                        self.stdout.write(f"  ... and {len(rows) - 5} more rows")
                else:
                    # Actually import
                    summary = importer.import_csv(
                        file_stream=f,
                        filename=csv_path.split("/")[-1],
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\nImport completed:"
                            f"\n  Total rows: {summary.total_rows}"
                            f"\n  Imported: {summary.imported}"
                            f"\n  Skipped (duplicates): {summary.skipped}"
                            f"\n  Errors: {summary.errors}"
                            f"\n  Duration: {summary.duration_seconds:.2f}s"
                            f"\n  Batch ID: {summary.batch_id}"
                        )
                    )

                    if summary.error_details:
                        self.stdout.write(self.style.WARNING("\nErrors:"))
                        for error in summary.error_details[:10]:
                            self.stdout.write(
                                f"  Row {error.get('row', '?')}: {error.get('error', 'Unknown error')}"
                            )

                        if len(summary.error_details) > 10:
                            self.stdout.write(
                                f"  ... and {len(summary.error_details) - 10} more errors"
                            )

        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Import failed: {e}")
