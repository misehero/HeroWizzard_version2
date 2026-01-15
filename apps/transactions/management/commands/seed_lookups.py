"""
Management command to seed initial lookup data.

Usage:
    python manage.py seed_lookups
    python manage.py seed_lookups --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transactions.models import (CostDetail, Product, ProductSubgroup,
                                      Project)


class Command(BaseCommand):
    help = "Seed initial lookup data for transactions app"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing lookup data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing lookup data...")
            ProductSubgroup.objects.all().delete()
            Product.objects.all().delete()
            Project.objects.all().delete()
            CostDetail.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        with transaction.atomic():
            self._seed_projects()
            self._seed_products()
            self._seed_subgroups()
            self._seed_cost_details()

        self.stdout.write(self.style.SUCCESS("Successfully seeded all lookup data!"))

    def _seed_projects(self):
        """Seed Project lookup table."""
        self.stdout.write("Seeding projects...")

        projects = [
            {"id": "-", "name": "—", "description": "Bez projektu"},
            {"id": "4cfuture", "name": "4CFuture", "description": "Projekt 4C Future"},
            {"id": "polcom", "name": "POLCOM", "description": "Projekt POLCOM"},
            {"id": "gap", "name": "GAP", "description": "Projekt GAP"},
            {"id": "larpic", "name": "LARPIC", "description": "Projekt LARPIC"},
            {"id": "cc", "name": "CC", "description": "Projekt CC"},
            {"id": "digitmi", "name": "Digitmi", "description": "Projekt Digitmi"},
            {"id": "omf", "name": "OMF", "description": "Projekt OMF"},
            {"id": "egr", "name": "EGR", "description": "Projekt EGR"},
            {
                "id": "digisecure",
                "name": "DIGISECURE",
                "description": "Projekt DIGISECURE",
            },
        ]

        for p in projects:
            Project.objects.update_or_create(
                id=p["id"],
                defaults={"name": p["name"], "description": p["description"]},
            )

        self.stdout.write(f"  Created/updated {len(projects)} projects")

    def _seed_products(self):
        """Seed Product lookup table."""
        self.stdout.write("Seeding products...")

        products = [
            # ŠKOLY category
            {
                "id": "silny-lidr",
                "name": "Silný lídr",
                "category": "SKOLY",
                "description": "Program Silný lídr pro školy",
            },
            {
                "id": "na-jedne-lodi",
                "name": "Na jedné lodi",
                "category": "SKOLY",
                "description": "Program Na jedné lodi pro školy",
            },
            # FIRMY category
            {
                "id": "talentova-akademie",
                "name": "Talentová akademie",
                "category": "FIRMY",
                "description": "Talentová akademie pro firmy",
            },
            {
                "id": "matrix",
                "name": "Matrix",
                "category": "FIRMY",
                "description": "Program Matrix pro firmy",
            },
        ]

        for p in products:
            Product.objects.update_or_create(
                id=p["id"],
                defaults={
                    "name": p["name"],
                    "category": p["category"],
                    "description": p["description"],
                },
            )

        self.stdout.write(f"  Created/updated {len(products)} products")

    def _seed_subgroups(self):
        """Seed ProductSubgroup lookup table."""
        self.stdout.write("Seeding product subgroups...")

        # Get products for foreign key references
        products = {p.id: p for p in Product.objects.all()}

        subgroups = [
            # Subgroups for Silný lídr
            {
                "id": "silny-lidr-analyza",
                "product_id": "silny-lidr",
                "name": "Analýza",
                "description": "Analytická fáze",
            },
            {
                "id": "silny-lidr-evaluace",
                "product_id": "silny-lidr",
                "name": "Evaluace",
                "description": "Evaluační fáze",
            },
            {
                "id": "silny-lidr-followup",
                "product_id": "silny-lidr",
                "name": "FollowUp",
                "description": "Následná péče",
            },
            {
                "id": "silny-lidr-feedback",
                "product_id": "silny-lidr",
                "name": "Feedback",
                "description": "Zpětná vazba",
            },
            {
                "id": "silny-lidr-metodika",
                "product_id": "silny-lidr",
                "name": "Metodika",
                "description": "Metodická podpora",
            },
            # Subgroups for Na jedné lodi
            {
                "id": "na-jedne-lodi-analyza",
                "product_id": "na-jedne-lodi",
                "name": "Analýza",
                "description": "Analytická fáze",
            },
            {
                "id": "na-jedne-lodi-najl",
                "product_id": "na-jedne-lodi",
                "name": "Na jedné lodi",
                "description": "Hlavní program",
            },
            {
                "id": "na-jedne-lodi-evaluace",
                "product_id": "na-jedne-lodi",
                "name": "Evaluace",
                "description": "Evaluační fáze",
            },
            {
                "id": "na-jedne-lodi-followup",
                "product_id": "na-jedne-lodi",
                "name": "FollowUp",
                "description": "Následná péče",
            },
            {
                "id": "na-jedne-lodi-feedback",
                "product_id": "na-jedne-lodi",
                "name": "Feedback",
                "description": "Zpětná vazba",
            },
            {
                "id": "na-jedne-lodi-metodika",
                "product_id": "na-jedne-lodi",
                "name": "Metodika",
                "description": "Metodická podpora",
            },
            # Subgroups for Talentová akademie
            {
                "id": "ta-analyza",
                "product_id": "talentova-akademie",
                "name": "Analýza",
                "description": "Analytická fáze",
            },
            {
                "id": "ta-evaluace",
                "product_id": "talentova-akademie",
                "name": "Evaluace",
                "description": "Evaluační fáze",
            },
            {
                "id": "ta-followup",
                "product_id": "talentova-akademie",
                "name": "FollowUp",
                "description": "Následná péče",
            },
            # Subgroups for Matrix
            {
                "id": "matrix-analyza",
                "product_id": "matrix",
                "name": "Analýza",
                "description": "Analytická fáze",
            },
            {
                "id": "matrix-evaluace",
                "product_id": "matrix",
                "name": "Evaluace",
                "description": "Evaluační fáze",
            },
            {
                "id": "matrix-followup",
                "product_id": "matrix",
                "name": "FollowUp",
                "description": "Následná péče",
            },
        ]

        for s in subgroups:
            if s["product_id"] in products:
                ProductSubgroup.objects.update_or_create(
                    id=s["id"],
                    defaults={
                        "product": products[s["product_id"]],
                        "name": s["name"],
                        "description": s["description"],
                    },
                )

        self.stdout.write(f"  Created/updated {len(subgroups)} subgroups")

    def _seed_cost_details(self):
        """Seed CostDetail lookup table."""
        self.stdout.write("Seeding cost details...")

        cost_details = [
            # Výdaje (Expenses)
            {
                "id": "vydaje-fixni",
                "druh_type": "vydaje",
                "druh_value": "Fixní",
                "detail": "Fixní náklady",
            },
            {
                "id": "vydaje-variabilni",
                "druh_type": "vydaje",
                "druh_value": "Variabilní",
                "detail": "Variabilní náklady",
            },
            {
                "id": "vydaje-mzdy",
                "druh_type": "vydaje",
                "druh_value": "Mzdy",
                "detail": "Mzdové náklady",
            },
            {
                "id": "vydaje-mimoradne",
                "druh_type": "vydaje",
                "druh_value": "Mimořádné",
                "detail": "Mimořádné náklady",
            },
            {
                "id": "vydaje-dluhy",
                "druh_type": "vydaje",
                "druh_value": "Dluhy",
                "detail": "Splátky dluhů",
            },
            {
                "id": "vydaje-prevod",
                "druh_type": "vydaje",
                "druh_value": "Převod",
                "detail": "Převody mezi účty",
            },
            # Příjmy (Income)
            {
                "id": "prijmy-projekt-eu",
                "druh_type": "prijmy",
                "druh_value": "Projekt EU",
                "detail": "Příjmy z EU projektů",
            },
            {
                "id": "prijmy-grant-cz",
                "druh_type": "prijmy",
                "druh_value": "Grant CZ",
                "detail": "Příjmy z českých grantů",
            },
            {
                "id": "prijmy-produkt",
                "druh_type": "prijmy",
                "druh_value": "Produkt",
                "detail": "Příjmy z produktů",
            },
            {
                "id": "prijmy-konference",
                "druh_type": "prijmy",
                "druh_value": "Konference",
                "detail": "Příjmy z konferencí",
            },
        ]

        for cd in cost_details:
            CostDetail.objects.update_or_create(
                id=cd["id"],
                defaults={
                    "druh_type": cd["druh_type"],
                    "druh_value": cd["druh_value"],
                    "detail": cd["detail"],
                },
            )

        self.stdout.write(f"  Created/updated {len(cost_details)} cost details")
