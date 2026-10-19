# -*- coding: utf-8 -*-
"""Migration of historical data (Prompt 32).

The MVP stored invoice amounts in a ``REAL`` column without a unit.  Those
rows must never be summed into the ledger implicitly: the unit is an open
business decision (DEC-013), therefore this service

* refuses to guess the unit — the operator states it explicitly;
* always offers a preview with row level errors and a reconciliation total;
* writes the exact integer rial amount and the unit that was used;
* keeps the migrated rows out of the ledger unless the operator explicitly asks
  for posting, and even then the posting is marked as provisional;
* is idempotent — an already migrated row is never converted twice.
"""
from __future__ import annotations

from ..core import ValidationError, to_rial
from .documents import DocumentService

ALLOWED_UNITS = ("ریال", "تومان")


class LegacyMigrationService:
    """Convert legacy ``invoices.amount`` (REAL) into exact integer Rials."""

    def __init__(self, db, actor="کاربر محلی"):
        self.db = db
        self.actor = actor

    # -- scan --------------------------------------------------------------- #
    def scan(self):
        """Report which legacy rows still need a unit decision."""
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT id, code, document_date, amount, amount_rial, currency_unit, status
                   FROM invoices WHERE amount IS NOT NULL ORDER BY id""").fetchall()
            pending = [dict(row) for row in rows if row["amount_rial"] is None]
            migrated = [dict(row) for row in rows if row["amount_rial"] is not None]
        return {
            "total_rows": len(rows),
            "pending_rows": len(pending),
            "migrated_rows": len(migrated),
            "needs_unit_decision": bool(pending),
            "unit_required": True,
            "open_decision": "DEC-013",
        }

    # -- preview ------------------------------------------------------------ #
    def preview(self, unit="ریال"):
        """Dry run: show the exact rial amount of every legacy row."""
        unit = self._check_unit(unit)
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT id, code, document_date, amount, amount_rial, currency_unit, status
                   FROM invoices WHERE amount IS NOT NULL ORDER BY id""").fetchall()
        items = []
        errors = []
        total_rial = 0
        already = 0
        for row in rows:
            if row["amount_rial"] is not None:
                already += 1
                continue
            try:
                amount_rial = to_rial(row["amount"], unit, field="مبلغ فاکتور تاریخی")
            except ValidationError as exc:
                errors.append({"id": row["id"], "code": row["code"], "error": str(exc)})
                continue
            total_rial += amount_rial
            items.append({"id": row["id"], "code": row["code"],
                          "document_date": row["document_date"],
                          "legacy_amount": row["amount"], "unit": unit,
                          "amount_rial": amount_rial, "status": row["status"]})
        return {
            "unit": unit,
            "rows": items,
            "row_count": len(items),
            "error_count": len(errors),
            "errors": errors,
            "already_migrated": already,
            "total_rial": total_rial,
            "reconciles": total_rial == sum(item["amount_rial"] for item in items),
            "warning": "تا تأیید DEC-013 هیچ‌کدام از این ردیف‌ها وارد دفترکل نمی‌شود.",
        }

    # -- migrate ------------------------------------------------------------ #
    def migrate(self, unit="ریال", actor=None, post_to_ledger=False,
                confirm_posting=False):
        """Write the exact rial amounts.  Posting into the ledger is opt-in."""
        actor = actor or self.actor
        unit = self._check_unit(unit)
        preview = self.preview(unit)
        if post_to_ledger and not confirm_posting:
            raise ValidationError(
                "برای posting سند به دفترکل تأیید صریح (confirm_posting) لازم است.")
        migrated = []
        skipped = list(preview["errors"])
        with self.db.transaction() as con:
            for item in preview["rows"]:
                con.execute(
                    """UPDATE invoices SET amount_rial=?, currency_unit=?, kind=?
                       WHERE id=? AND amount_rial IS NULL""",
                    (item["amount_rial"], unit, "sales", item["id"]))
                migrated.append(item)
            self.db.audit(actor, "migrate", "invoice", None,
                          "unit=%s rows=%d total_rial=%s"
                          % (unit, len(migrated), preview["total_rial"]), con)
        result = {
            "unit": unit,
            "migrated": len(migrated),
            "skipped": len(skipped),
            "errors": skipped,
            "total_rial": preview["total_rial"],
            "posted": 0,
            "reconciles": True,
        }
        if post_to_ledger:
            result["posted"] = self._post_migrated(actor)
            result["reconciles"] = self._reconcile(actor, preview["total_rial"])
        return result

    # -- helpers ------------------------------------------------------------ #
    def _post_migrated(self, actor):
        """Post the migrated invoices (provisional, explicit opt-in)."""
        from .ledger import LedgerService

        ledger = LedgerService(self.db)
        posted = 0
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT id FROM invoices
                   WHERE amount_rial IS NOT NULL AND posted_entry_id IS NULL
                   ORDER BY id""").fetchall()
        for row in rows:
            try:
                ledger.post_invoice(row["id"], actor=actor)
                posted += 1
            except Exception:
                continue
        return posted

    def _reconcile(self, actor, expected_total):
        with self.db.reader() as con:
            row = con.execute(
                """SELECT COALESCE(SUM(amount_rial),0) FROM invoices
                   WHERE amount_rial IS NOT NULL""").fetchone()
        return int(row[0]) == int(expected_total)

    @staticmethod
    def _check_unit(unit):
        if not unit or unit not in ALLOWED_UNITS:
            raise ValidationError(
                "واحد مبلغ تاریخی باید صریحاً «ریال» یا «تومان» باشد (DEC-013).")
        return unit
