# -*- coding: utf-8 -*-
"""Commercial documents: sales/purchase invoices (with lines) and expenses.

Money rules (Prompt 16 / MONEY_UNIT_POLICY):

* every amount is stored as **integer rials** in ``amount_rial``;
* the legacy ``invoices.amount`` REAL column is kept in sync for backward
  compatibility but is never used for reporting; rows created before the
  rial migration have ``amount_rial = NULL`` and stay out of every financial
  report until the unit is reconciled (DEC-013);
* the header total is always derived from the lines - it can never be typed in
  by hand.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso, to_rial

#: Technical rounding rule used for weight x price.  The commercial rounding
#: policy still has to be approved by the accountant (DEC-005); changing this
#: constant requires a migration + a new test run.
ROUNDING_MODE = ROUND_HALF_UP
ROUNDING_POLICY_VERSION = "half-up-v1"

INVOICE_STATUS = ("draft", "confirmed", "cancelled")


def round_rial(value):
    """Round a Decimal amount to integer rials with the documented policy."""
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUNDING_MODE))


class DocumentService:
    """Invoices (sales, purchase, service) and expenses."""

    def __init__(self, db):
        self.db = db

    # -- invoices ----------------------------------------------------------- #
    def create_invoice(self, party_id, kind="sales", document_date=None, lines=None,
                       invoice_type="فروش", description="", shipment_id=None,
                       status="draft", doc_number=None, unit="ریال", notes=None,
                       due_date=None, actor="کاربر محلی"):
        """Create an invoice with lines.  The total is computed, never typed."""
        if kind not in ("sales", "purchase", "service"):
            raise ValidationError("نوع سند نامعتبر است: %s" % kind)
        if status not in INVOICE_STATUS:
            raise ValidationError("وضعیت سند نامعتبر است: %s" % status)
        lines = lines or []
        if not lines:
            raise ValidationError("حداقل یک ردیف سند لازم است.")
        stamp = now_iso()
        document_date = normalize_iso_date(document_date or stamp[:10], "تاریخ سند")
        if due_date:
            due_date = normalize_iso_date(due_date, "تاریخ سررسید")
        prepared = []
        for index, line in enumerate(lines, 1):
            prepared.append(self._prepare_line(line, index, unit))
        total_rial = sum(item["line_total_rial"] for item in prepared)
        with self.db.transaction() as con:
            if not con.execute("SELECT 1 FROM parties WHERE id=?", (party_id,)).fetchone():
                raise ValidationError("طرف حساب وجود ندارد.")
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM invoices").fetchone()
            code = "INV-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO invoices(code, party_id, invoice_type, document_date, amount,
                        description, shipment_id, status, created_at, created_by, amount_rial,
                        currency_unit, doc_number, kind, notes, due_date)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, party_id, invoice_type, document_date, float(total_rial),
                 str(description or "").strip() or None, shipment_id,
                 {"draft": "پیش‌نویس", "confirmed": "قطعی", "cancelled": "لغوشده"}[status],
                 stamp, actor, total_rial, "IRR", str(doc_number or "").strip() or None,
                 kind, str(notes or "").strip() or None, due_date))
            invoice_id = cur.lastrowid
            for item in prepared:
                con.execute(
                    """INSERT INTO invoice_lines(invoice_id, product_id, grade_id, packaging_id,
                            description, quantity, unit, unit_price_rial, weight_kg,
                            billing_weight_kg, discount_rial, line_total_rial, shipment_id,
                            sort_order, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (invoice_id, item["product_id"], item["grade_id"], item["packaging_id"],
                     item["description"], item["quantity"], item["unit"],
                     item["unit_price_rial"], item["weight_kg"], item["billing_weight_kg"],
                     item["discount_rial"], item["line_total_rial"], item["shipment_id"],
                     item["sort_order"], stamp))
            self.db.audit(actor, "create", "invoice", invoice_id,
                          "%s; %s; %d rial" % (code, kind, total_rial), con)
            return invoice_id

    def _prepare_line(self, line, index, unit):
        unit_price_rial = to_rial(line.get("unit_price", 0), unit, "قیمت واحد")
        discount_rial = to_rial(line.get("discount_rial", line.get("discount", 0)), "ریال",
                                "تخفیف ردیف")
        try:
            quantity = float(line.get("quantity", 0) or 0)
            weight_kg = float(line.get("weight_kg", 0) or 0)
        except (TypeError, ValueError):
            raise ValidationError("مقدار ردیف %d معتبر نیست." % index)
        if quantity < 0 or weight_kg < 0:
            raise ValidationError("مقدار ردیف %d نمی‌تواند منفی باشد." % index)
        billing_weight = line.get("billing_weight_kg")
        if billing_weight is None:
            billing_weight = weight_kg
        billing_weight = float(billing_weight or 0)
        if billing_weight < 0:
            raise ValidationError("وزن قابل صورتحساب ردیف %d نمی‌تواند منفی باشد." % index)
        gross = Decimal(str(billing_weight)) * Decimal(unit_price_rial)
        total = round_rial(gross) - discount_rial
        if total < 0:
            raise ValidationError("تخفیف ردیف %d از مبلغ سند بیشتر است." % index)
        return {
            "product_id": line.get("product_id"),
            "grade_id": line.get("grade_id"),
            "packaging_id": line.get("packaging_id"),
            "description": str(line.get("description") or "").strip() or None,
            "quantity": quantity,
            "unit": line.get("unit") or "کیلوگرم",
            "unit_price_rial": unit_price_rial,
            "weight_kg": weight_kg,
            "billing_weight_kg": billing_weight,
            "discount_rial": discount_rial,
            "line_total_rial": total,
            "shipment_id": line.get("shipment_id"),
            "sort_order": index,
        }

    def confirm_invoice(self, invoice_id, actor="کاربر محلی"):
        """Approve an invoice so that it can be posted to the ledger."""
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
            if not row:
                raise ValidationError("سند یافت نشد.")
            if row["status"] == "قطعی":
                return True
            if row["status"] == "لغوشده":
                raise ConflictError("سند لغوشده قابل قطعی‌کردن نیست.")
            if row["amount_rial"] is None:
                raise ConflictError("سند legacy بدون واحد مصوب به دفترکل متصل نمی‌شود (DEC-013).")
            con.execute(
                """UPDATE invoices SET status='قطعی', approved_by=?, notes=COALESCE(notes,'') WHERE id=?""",
                (actor, invoice_id))
            self.db.audit(actor, "confirm", "invoice", invoice_id, row["code"], con)
            return True

    def cancel_invoice(self, invoice_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT status, posted_entry_id, code FROM invoices WHERE id=?",
                              (invoice_id,)).fetchone()
            if not row:
                raise ValidationError("سند یافت نشد.")
            if row["posted_entry_id"]:
                raise ConflictError("سند posting‌شده قابل لغو مستقیم نیست؛ ابتدا سند را برگردانید.")
            con.execute("UPDATE invoices SET status='لغوشده' WHERE id=?", (invoice_id,))
            self.db.audit(actor, "cancel", "invoice", invoice_id, row["code"], con)
            return True

    def list_invoices(self, kind=None, status=None, party_id=None, limit=200):
        clauses, params = [], []
        if kind:
            clauses.append("i.kind=?")
            params.append(kind)
        if status:
            clauses.append("i.status=?")
            params.append(status)
        if party_id:
            clauses.append("i.party_id=?")
            params.append(party_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(int(limit))
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT i.*, p.display_name AS party_name FROM invoices i
                   JOIN parties p ON p.id=i.party_id""" + where +
                " ORDER BY i.id DESC LIMIT ?", params).fetchall()
        return [dict(r) for r in rows]

    def get_invoice(self, invoice_id):
        with self.db.reader() as con:
            head = con.execute(
                """SELECT i.*, p.display_name AS party_name FROM invoices i
                   JOIN parties p ON p.id=i.party_id WHERE i.id=?""", (invoice_id,)).fetchone()
            if not head:
                return None
            lines = con.execute(
                "SELECT * FROM invoice_lines WHERE invoice_id=? ORDER BY sort_order, id",
                (invoice_id,)).fetchall()
        result = dict(head)
        result["lines"] = [dict(l) for l in lines]
        return result

    def invoice_total_rial(self, invoice_id):
        """Total recomputed from the lines (the header is never trusted blindly)."""
        with self.db.reader() as con:
            row = con.execute(
                "SELECT COALESCE(SUM(line_total_rial),0) FROM invoice_lines WHERE invoice_id=?",
                (invoice_id,)).fetchone()
        return int(row[0])

    # -- expenses ----------------------------------------------------------- #
    def create_expense(self, category, amount_rial, expense_date=None, party_id=None,
                       payment_method="cash", is_billable=False, note="", unit="ریال",
                       actor="کاربر محلی"):
        """Record a real expense (not a settlement deduction)."""
        amount = to_rial(amount_rial, unit, "مبلغ هزینه")
        if amount <= 0:
            raise ValidationError("مبلغ هزینه باید بزرگ‌تر از صفر باشد.")
        stamp = now_iso()
        expense_date = normalize_iso_date(expense_date or stamp[:10], "تاریخ هزینه")
        with self.db.transaction() as con:
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM expenses").fetchone()
            code = "EXP-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO expenses(code, category, amount_rial, expense_date, party_id,
                        payment_method, status, is_billable, note, created_at, created_by)
                   VALUES(?,?,?,?,?,?, 'recorded', ?,?,?,?)""",
                (code, str(category or "").strip() or "سایر", amount, expense_date, party_id,
                 payment_method, int(bool(is_billable)), str(note or "").strip() or None,
                 stamp, actor))
            self.db.audit(actor, "create", "expense", cur.lastrowid,
                          "%s; %d rial" % (code, amount), con)
            return cur.lastrowid

    def allocate_expense(self, expense_id, target_type, target_id, amount_rial,
                          method="manual", actor="کاربر محلی"):
        """Allocate an expense to a shipment/cost centre.  Allocations must sum
        to the expense amount (checked by the invariant test-suite)."""
        amount = to_rial(amount_rial, "ریال", "مبلغ تخصیص")
        if amount <= 0:
            raise ValidationError("مبلغ تخصیص باید بزرگ‌تر از صفر باشد.")
        with self.db.transaction() as con:
            expense = con.execute("SELECT amount_rial FROM expenses WHERE id=?",
                                   (expense_id,)).fetchone()
            if not expense:
                raise ValidationError("هزینه یافت نشد.")
            allocated = con.execute(
                "SELECT COALESCE(SUM(amount_rial),0) FROM expense_allocations WHERE expense_id=?",
                (expense_id,)).fetchone()[0]
            if allocated + amount > int(expense["amount_rial"]):
                raise ValidationError("مجموع تخصیص‌ها از مبلغ هزینه بیشتر می‌شود.")
            cur = con.execute(
                """INSERT INTO expense_allocations(expense_id, target_type, target_id, amount_rial,
                        method, created_at) VALUES(?,?,?,?,?,?)""",
                (expense_id, target_type, target_id, amount, method, now_iso()))
            self.db.audit(actor, "allocate", "expense", expense_id,
                          "%s=%d rial" % (target_type, amount), con)
            return cur.lastrowid

    def list_expenses(self, limit=200):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT e.*, p.display_name AS party_name FROM expenses e
                   LEFT JOIN parties p ON p.id=e.party_id ORDER BY e.id DESC LIMIT ?""",
                (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def expense_allocations(self, expense_id):
        with self.db.reader() as con:
            rows = con.execute(
                "SELECT * FROM expense_allocations WHERE expense_id=? ORDER BY id",
                (expense_id,)).fetchall()
        return [dict(r) for r in rows]
