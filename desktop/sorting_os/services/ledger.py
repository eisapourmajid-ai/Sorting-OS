# -*- coding: utf-8 -*-
"""Posting bridge between operational documents and the double-entry ledger.

The operational layer never writes journal rows directly: it asks this
service, which builds a balanced entry, posts it through the accounting core
and links the result back to the source document.  Two rules are enforced
here:

* **Idempotency** - every posting carries ``source_type``/``source_id``; the
  ledger has a unique index on that pair, so a retry can never create a
  second movement (Prompt 17, spec section 4.4).
* **No invented accounting policy** - where a commercial decision is still
  open (inventory valuation DEC-006, cash-flow classification DEC-012) the
  posting is marked *provisional* and the open decision is reported back to
  the caller instead of being silently applied.
"""
from __future__ import annotations

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso

#: Account codes used by the posting policy.
ACCOUNT_CASH = "1000"
ACCOUNT_BANK = "1010"
ACCOUNT_RECEIVABLE = "1100"
ACCOUNT_INVENTORY = "1200"
ACCOUNT_PREPAID = "1300"
ACCOUNT_PAYABLE = "2000"
ACCOUNT_REVENUE = "4000"
ACCOUNT_EXPENSE = "6000"
ACCOUNT_BANK_FEE = "6100"

#: Policy for posting an invoice of each kind.
INVOICE_POLICY = {
    "sales": {
        "debit": ACCOUNT_RECEIVABLE,
        "credit": ACCOUNT_REVENUE,
        "label": "فروش/خدمات به طرف حساب",
    },
    "service": {
        "debit": ACCOUNT_RECEIVABLE,
        "credit": ACCOUNT_REVENUE,
        "label": "ارائه خدمات سورتینگ",
    },
    "purchase": {
        "debit": ACCOUNT_PREPAID,
        "credit": ACCOUNT_PAYABLE,
        "label": "خرید کالا/خدمات (نامشخص تا تعیین مدل مالکیت)",
    },
}

#: Expenses map to an operational expense account.
EXPENSE_ACCOUNTS = {
    "حمل": ACCOUNT_EXPENSE,
    "کارگری": ACCOUNT_EXPENSE,
    "باربری": ACCOUNT_EXPENSE,
    "بانکی": ACCOUNT_BANK_FEE,
    "عمومی": ACCOUNT_EXPENSE,
}


class LedgerService:
    """Post operational documents into the double-entry ledger."""

    def __init__(self, db, book=None):
        self.db = db
        if book is None:
            from accounting_core import AccountingBook

            book = AccountingBook(db.path)
        self.book = book

    # -- helpers ------------------------------------------------------------ #
    def entry_for_source(self, source_type, source_id):
        """Return the posted entry of a source document (if any)."""
        with self.book.connect() as con:
            row = con.execute(
                "SELECT * FROM journal_entries WHERE source_type=? AND source_id=?",
                (source_type, str(source_id))).fetchone()
        return dict(row) if row else None

    def _post(self, entry_date, description, lines, source_type, source_id, actor):
        """Post an entry; a repeated source is not an error but not a new entry."""
        existing = self.entry_for_source(source_type, source_id)
        if existing:
            return existing["id"], False
        try:
            entry_id = self.book.post_entry(
                entry_date, description, lines, actor=actor,
                source_type=source_type, source_id=str(source_id))
        except ValueError as exc:
            if "تکرار" in str(exc):
                existing = self.entry_for_source(source_type, source_id)
                if existing:
                    return existing["id"], False
            raise
        return entry_id, True

    # -- invoices ----------------------------------------------------------- #
    def post_invoice(self, invoice_id, actor="کاربر محلی"):
        """Post a confirmed invoice to the ledger (idempotent)."""
        with self.db.reader() as con:
            invoice = con.execute(
                """SELECT i.*, p.display_name AS party_name, s.ownership_model
                   FROM invoices i JOIN parties p ON p.id=i.party_id
                   LEFT JOIN shipments s ON s.id=i.shipment_id WHERE i.id=?""",
                (invoice_id,)).fetchone()
        if not invoice:
            raise ValidationError("سند یافت نشد.")
        if invoice["status"] == "لغوشده":
            raise ConflictError("سند لغوشده قابل posting نیست.")
        if invoice["status"] != "قطعی":
            raise ConflictError("فقط سند قطعی قابل posting است.")
        if invoice["amount_rial"] is None:
            raise ConflictError("سند legacy بدون واحد مصوب به دفترکل متصل نمی‌شود (DEC-013).")
        amount = int(invoice["amount_rial"])
        if amount <= 0:
            raise ValidationError("مبلغ سند باید بزرگ‌تر از صفر باشد.")
        kind = invoice["kind"] or "sales"
        policy = INVOICE_POLICY.get(kind)
        if not policy:
            raise ValidationError("نوع سند پشتیبانی نمی‌شود: %s" % kind)
        notes = []
        debit_account = policy["debit"]
        if kind == "purchase":
            ownership = invoice["ownership_model"] or "undetermined"
            if ownership == "buy_sell":
                debit_account = ACCOUNT_INVENTORY
                notes.append("بهای تمام‌شده و ارزش‌گذاری موجودی هنوز مصوب نشده است (DEC-006).")
            else:
                notes.append(
                    "مدل مالکیت این محموله «%s» است؛ مبلغ موقتاً در حساب پیش‌پرداخت/تعلیق ثبت شد "
                    "(DEC-001/DEC-002)." % ownership)
        description = "%s - %s - %s" % (policy["label"], invoice["code"], invoice["party_name"])
        if notes:
            description += " | " + " ".join(notes)
        # The analytical party is attached to the receivable/payable line only:
        # the counter account (revenue, inventory) is not a party account.
        lines = [
            {"account_code": debit_account, "debit_rial": amount, "credit_rial": 0,
             "description": policy["label"], "party_ref": str(invoice["party_id"])},
            {"account_code": policy["credit"], "debit_rial": 0, "credit_rial": amount,
             "description": invoice["code"]},
        ]
        entry_id, created = self._post(
            invoice["document_date"], description, lines, "invoice", invoice_id, actor)
        if created:
            with self.db.transaction() as con:
                con.execute(
                    "UPDATE invoices SET posted_entry_id=?, posted_at=? WHERE id=?",
                    (entry_id, now_iso(), invoice_id))
                self.db.audit(actor, "post", "invoice", invoice_id,
                              "entry=%s amount=%d rial" % (entry_id, amount), con)
        return {"entry_id": entry_id, "created": created, "provisional": bool(notes),
                "notes": notes, "amount_rial": amount}

    # -- payments ----------------------------------------------------------- #
    def post_payment(self, payment_id, actor="کاربر محلی"):
        """Post a receipt/payment to the ledger (idempotent)."""
        with self.db.reader() as con:
            payment = con.execute(
                """SELECT p.*, b.code AS bank_code FROM payments p
                   LEFT JOIN bank_accounts b ON b.id=p.bank_account_id WHERE p.id=?""",
                (payment_id,)).fetchone()
        if not payment:
            raise ValidationError("پرداخت/دریافت یافت نشد.")
        amount = int(payment["amount_rial"])
        if amount <= 0:
            raise ValidationError("مبلغ پرداخت/دریافت باید بزرگ‌تر از صفر باشد.")
        if payment["direction"] == "in":
            cash_account = ACCOUNT_BANK if payment["bank_account_id"] else ACCOUNT_CASH
            lines = [
                {"account_code": cash_account, "debit_rial": amount, "credit_rial": 0,
                 "description": payment["code"]},
                {"account_code": ACCOUNT_RECEIVABLE, "debit_rial": 0, "credit_rial": amount,
                 "description": "تسویه مطالبات", "party_ref": str(payment["party_id"])},
            ]
            label = "دریافت وجه"
        else:
            cash_account = ACCOUNT_BANK if payment["bank_account_id"] else ACCOUNT_CASH
            lines = [
                {"account_code": ACCOUNT_PAYABLE, "debit_rial": amount, "credit_rial": 0,
                 "description": "تسویه بدهی", "party_ref": str(payment["party_id"])},
                {"account_code": cash_account, "debit_rial": 0, "credit_rial": amount,
                 "description": payment["code"]},
            ]
            label = "پرداخت وجه"
        entry_id, created = self._post(
            payment["payment_date"], "%s - %s" % (label, payment["code"]), lines,
            "payment", payment_id, actor)
        if created:
            with self.db.transaction() as con:
                con.execute("UPDATE payments SET posted_entry_id=? WHERE id=?",
                            (entry_id, payment_id))
                self.db.audit(actor, "post", "payment", payment_id,
                              "entry=%s amount=%d rial" % (entry_id, amount), con)
        return {"entry_id": entry_id, "created": created, "amount_rial": amount}

    # -- expenses ----------------------------------------------------------- #
    def post_expense(self, expense_id, actor="کاربر محلی"):
        """Post a recorded expense (recognised once, never twice)."""
        with self.db.reader() as con:
            expense = con.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if not expense:
            raise ValidationError("هزینه یافت نشد.")
        if expense["recognized_entry_id"]:
            return {"entry_id": expense["recognized_entry_id"], "created": False}
        if expense["status"] == "cancelled":
            raise ConflictError("هزینه لغوشده قابل posting نیست.")
        amount = int(expense["amount_rial"])
        account = EXPENSE_ACCOUNTS.get(expense["category"], ACCOUNT_EXPENSE)
        cash_account = ACCOUNT_BANK if expense["payment_method"] == "bank" else ACCOUNT_CASH
        lines = [
            {"account_code": account, "debit_rial": amount, "credit_rial": 0,
             "description": expense["category"]},
            {"account_code": cash_account, "debit_rial": 0, "credit_rial": amount,
             "description": expense["code"]},
        ]
        entry_id, created = self._post(
            expense["expense_date"], "هزینه %s - %s" % (expense["category"], expense["code"]),
            lines, "expense", expense_id, actor)
        if created:
            with self.db.transaction() as con:
                con.execute("UPDATE expenses SET recognized_entry_id=?, status='paid' WHERE id=?",
                            (entry_id, expense_id))
                self.db.audit(actor, "post", "expense", expense_id,
                              "entry=%s amount=%d rial" % (entry_id, amount), con)
        return {"entry_id": entry_id, "created": created, "amount_rial": amount}

    # -- reversals ---------------------------------------------------------- #
    def reverse_source(self, source_type, source_id, reversal_date, reason, actor="کاربر محلی"):
        """Reverse a posted source document with an offsetting entry."""
        entry = self.entry_for_source(source_type, source_id)
        if not entry:
            raise ValidationError("سند مرتبط یافت نشد.")
        reversal_id = self.book.reverse_entry(
            entry["id"], normalize_iso_date(reversal_date, "تاریخ برگشت"), reason, actor=actor)
        with self.db.transaction() as con:
            self.db.audit(actor, "reverse", source_type, source_id,
                          "reversal entry=%s: %s" % (reversal_id, reason), con)
        return {"reversal_entry_id": reversal_id, "reversed_entry_id": entry["id"]}

    # -- reporting ---------------------------------------------------------- #
    def party_subledger(self, party_id, date_from=None, date_to=None):
        """Party statement reconstructed from the posted ledger."""
        clauses, params = ["l.party_ref = ?", "e.status='posted'"], [str(party_id)]
        if date_from:
            clauses.append("e.entry_date >= ?")
            params.append(normalize_iso_date(date_from, "از تاریخ"))
        if date_to:
            clauses.append("e.entry_date <= ?")
            params.append(normalize_iso_date(date_to, "تا تاریخ"))
        with self.book.connect() as con:
            rows = con.execute(
                """SELECT e.entry_no, e.entry_date, e.description, e.source_type, e.source_id,
                          l.account_code, a.name AS account_name, l.description AS line_description,
                          l.debit_rial, l.credit_rial
                   FROM journal_lines l
                   JOIN journal_entries e ON e.id = l.entry_id
                   JOIN accounting_accounts a ON a.code = l.account_code
                   WHERE """ + " AND ".join(clauses) +
                " ORDER BY e.entry_date, e.id, l.line_no", params).fetchall()
        debit = sum(int(r["debit_rial"]) for r in rows)
        credit = sum(int(r["credit_rial"]) for r in rows)
        return {"party_id": party_id, "lines": [dict(r) for r in rows],
                "debit_rial": debit, "credit_rial": credit, "balance_rial": debit - credit}

    def open_items(self, party_id, as_of=None):
        """Open invoices of a party (documents minus received amounts)."""
        with self.db.reader() as con:
            invoices = con.execute(
                """SELECT i.*, p.display_name AS party_name FROM invoices i
                   JOIN parties p ON p.id=i.party_id
                   WHERE i.party_id=? AND i.status='قطعی' AND i.amount_rial IS NOT NULL
                   ORDER BY i.document_date, i.id""", (party_id,)).fetchall()
            payments = con.execute(
                """SELECT COALESCE(SUM(amount_rial),0) FROM payments
                   WHERE party_id=? AND direction='in'""", (party_id,)).fetchone()[0]
        items = []
        for invoice in invoices:
            items.append({
                "invoice_id": invoice["id"],
                "code": invoice["code"],
                "document_date": invoice["document_date"],
                "due_date": invoice["due_date"],
                "amount_rial": int(invoice["amount_rial"]),
                "kind": invoice["kind"],
            })
        return {"party_id": party_id, "items": items, "total_rial": int(payments)}

    def reconcile_postings(self, actor="کاربر محلی"):
        """Relink invoices/payments whose journal entry exists but whose link
        was lost (e.g. a crash between posting and the link update)."""
        repaired = 0
        with self.db.transaction() as con:
            rows = con.execute(
                """SELECT id FROM invoices WHERE posted_entry_id IS NULL
                   AND id IN (SELECT CAST(source_id AS INTEGER) FROM journal_entries
                              WHERE source_type='invoice')""").fetchall()
            for row in rows:
                entry = self.entry_for_source("invoice", row["id"])
                if entry:
                    con.execute("UPDATE invoices SET posted_entry_id=? WHERE id=?",
                                (entry["id"], row["id"]))
                    repaired += 1
            rows = con.execute(
                """SELECT id FROM payments WHERE posted_entry_id IS NULL
                   AND id IN (SELECT CAST(source_id AS INTEGER) FROM journal_entries
                              WHERE source_type='payment')""").fetchall()
            for row in rows:
                entry = self.entry_for_source("payment", row["id"])
                if entry:
                    con.execute("UPDATE payments SET posted_entry_id=? WHERE id=?",
                                (entry["id"], row["id"]))
                    repaired += 1
        return {"repaired": repaired}
