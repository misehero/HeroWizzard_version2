"""
Django management command for automated JSON backups.
Reuses the same export logic as the export_backup() API view.

Usage:
    python manage.py backup_to_json
    python manage.py backup_to_json --output /custom/path/
    python manage.py backup_to_json --keep 30
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.transactions.models import (
    CategoryRule,
    ImportBatch,
    Product,
    ProductSubgroup,
    Project,
    Transaction,
    TransactionAuditLog,
)


class Command(BaseCommand):
    help = "Export full application state to a JSON backup file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output directory (default: <project>/backups/)",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=30,
            help="Number of days to keep old backups (default: 30, 0=no cleanup)",
        )

    def handle(self, *args, **options):
        output_dir = options["output"]
        if not output_dir:
            output_dir = os.path.join(settings.BASE_DIR, "backups")

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"backup_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # --- Build backup payload (same logic as export_backup view) ---
        txn_records = []
        for t in (
            Transaction.objects.filter(is_deleted=False)
            .select_related("projekt", "produkt", "podskupina")
            .order_by("datum", "created_at")
            .iterator()
        ):
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
                        t.datum_zauctovani.isoformat()
                        if t.datum_zauctovani
                        else None
                    ),
                    "cislo_protiuctu": t.cislo_protiuctu,
                    "nazev_protiuctu": t.nazev_protiuctu,
                    "typ_transakce": t.typ_transakce,
                    "konstantni_symbol": t.konstantni_symbol,
                    "specificky_symbol": t.specificky_symbol,
                    "puvodni_castka": (
                        str(t.puvodni_castka) if t.puvodni_castka else None
                    ),
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
                    "import_batch_id": (
                        str(t.import_batch_id) if t.import_batch_id else None
                    ),
                    "created_at": (
                        t.created_at.isoformat() if t.created_at else None
                    ),
                }
            )

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
                    "set_mh_pct": (
                        str(r.set_mh_pct) if r.set_mh_pct is not None else None
                    ),
                    "set_sk_pct": (
                        str(r.set_sk_pct) if r.set_sk_pct is not None else None
                    ),
                    "set_xp_pct": (
                        str(r.set_xp_pct) if r.set_xp_pct is not None else None
                    ),
                    "set_fr_pct": (
                        str(r.set_fr_pct) if r.set_fr_pct is not None else None
                    ),
                    "set_projekt": r.set_projekt.name if r.set_projekt else None,
                    "set_produkt": r.set_produkt.name if r.set_produkt else None,
                    "set_podskupina": (
                        r.set_podskupina.name if r.set_podskupina else None
                    ),
                    "is_active": r.is_active,
                    "created_at": (
                        r.created_at.isoformat() if r.created_at else None
                    ),
                }
            )

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
                    "started_at": (
                        b.started_at.isoformat() if b.started_at else None
                    ),
                    "completed_at": (
                        b.completed_at.isoformat() if b.completed_at else None
                    ),
                    "created_at": (
                        b.created_at.isoformat() if b.created_at else None
                    ),
                }
            )

        audit_records = []
        for a in TransactionAuditLog.objects.select_related("user").order_by(
            "created_at"
        ):
            audit_records.append(
                {
                    "id": str(a.id),
                    "transaction_id": str(a.transaction_id),
                    "user_email": a.user.email if a.user else None,
                    "action": a.action,
                    "details": a.details,
                    "created_at": (
                        a.created_at.isoformat() if a.created_at else None
                    ),
                }
            )

        # --- Lookups ---
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

        payload = {
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
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        size_kb = os.path.getsize(filepath) / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup saved: {filepath} "
                f"({size_kb:.1f} KB, "
                f"{len(txn_records)} transactions, "
                f"{len(rule_records)} rules, "
                f"{len(batch_records)} batches, "
                f"{len(audit_records)} audit logs)"
            )
        )

        # --- Cleanup old backups ---
        keep_days = options["keep"]
        if keep_days > 0:
            cutoff = datetime.now() - timedelta(days=keep_days)
            removed = 0
            for f in Path(output_dir).glob("backup_*.json"):
                if f.stat().st_mtime < cutoff.timestamp():
                    f.unlink()
                    removed += 1
            if removed:
                self.stdout.write(f"Cleaned up {removed} old backup(s)")
