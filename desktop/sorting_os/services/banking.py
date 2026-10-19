# -*- coding: utf-8 -*-
"""Banking: accounts, statement import, reconciliation, cheques and payments.

Rules from ``docs/13-bank-transactions-import-and-checks.md`` and
``docs/financial/MONEY_UNIT_POLICY_FA.md``:

* the **unit of a statement is chosen explicitly** by the operator; the system
  never guesses the unit from the size of a number;
* importing the same file twice must not create a second document - the batch
  is identified by its checksum;
* every row keeps its own error, so a rejected row never blocks the file;
* a match is always a *suggestion* until a human accepts it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso, to_rial

DIRECTIONS = ("in", "out")


def _checksum(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()


class BankingService:
    """Bank accounts, statement import, matching, cheques and payments."""

    def __init__(self, db):
        self.db = db

    # -- bank accounts ------------------------------------------------------ #
    def create_bank_account(self, code, name, bank_name=None, account_number_masked=None,
                            actor="کاربر محلی"):
        code, name = str(code or "").strip(), str(name or "").strip()
        if not code or not name:
            raise ValidationError("کد و نام حساب بانکی الزامی است.")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM bank_accounts WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد حساب بانکی تکراری است: %s" % code)
            cur = con.execute(
                """INSERT INTO bank_accounts(code, name, bank_name, account_number_masked,
                        currency, is_active, created_at)
                   VALUES(?,?,?,?, 'IRR', 1, ?)""",
                (code, name, str(bank_name or "").strip() or None,
                 str(account_number_masked or "").strip() or None, now_iso()))
            self.db.audit(actor, "create", "bank_account", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_bank_accounts(self):
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY code").fetchall()]

    # -- statement import --------------------------------------------------- #
    def import_statement(self, bank_account_id, rows, unit, file_name=None, actor="کاربر محلی"):
        """Import a bank statement as a *preview* batch.

        Returns a dictionary with per-row results; nothing is committed to the
        ledger by this call.
        """
        if unit not in ("ریال", "تومان"):
            raise ValidationError("واحد مبلغ گردش بانکی باید صریحاً «ریال» یا «تومان» باشد.")
        if not rows:
            raise ValidationError("فایل گردش بانکی خالی است.")
        checksum = _checksum({"bank": bank_account_id, "unit": unit, "rows": rows})
        with self.db.reader() as con:
            existing = con.execute(
                "SELECT id, status FROM bank_statements WHERE bank_account_id=? AND checksum=?",
                (bank_account_id, checksum)).fetchone()
        if existing:
            return {"statement_id": existing["id"], "duplicate": True, "status": existing["status"],
                    "checksum": checksum, "rows": [], "errors": []}
        stamp = now_iso()
        prepared, errors = [], []
        for index, row in enumerate(rows, 1):
            try:
                tx_date = normalize_iso_date(row.get("date") or row.get("transaction_date"),
                                            "تاریخ تراکنش")
                direction = str(row.get("direction") or "").strip().lower()
                if direction in ("دریافت", "ورود", "credit", "in"):
                    direction = "in"
                elif direction in ("پرداخت", "خروج", "debit", "out"):
                    direction = "out"
                if direction not in DIRECTIONS:
                    raise ValidationError("جهت تراکنش نامعتبر است (in/out).")
                amount = to_rial(row.get("amount"), unit, "مبلغ تراکنش")
                if amount <= 0:
                    raise ValidationError("مبلغ تراکنش باید بزرگ‌تر از صفر باشد.")
                prepared.append({
                    "row_no": index,
                    "transaction_date": tx_date,
                    "description": str(row.get("description") or "").strip(),
                    "amount_rial": amount,
                    "direction": direction,
                    "reference": str(row.get("reference") or "").strip() or None,
                    "external_id": str(row.get("external_id") or "").strip() or None,
                })
            except (ValidationError, ValueError) as exc:
                errors.append({"row": index, "error": str(exc),
                               "raw": {k: v for k, v in row.items()}})
        with self.db.transaction() as con:
            cur = con.execute(
                """INSERT INTO bank_statements(bank_account_id, file_name, imported_at, imported_by,
                        unit, row_count, checksum, status, created_at)
                   VALUES(?,?,?,?,?,?,?, 'preview', ?)""",
                (bank_account_id, str(file_name or "").strip() or None, stamp, actor, unit,
                 len(prepared), checksum, stamp))
            statement_id = cur.lastrowid
            for item in prepared:
                con.execute(
                    """INSERT INTO bank_transactions(statement_id, row_no, transaction_date,
                            description, amount_rial, direction, reference, external_id, status,
                            created_at)
                       VALUES(?,?,?,?,?,?,?,?, 'unmatched', ?)""",
                    (statement_id, item["row_no"], item["transaction_date"], item["description"],
                     item["amount_rial"], item["direction"], item["reference"],
                     item["external_id"], stamp))
            self.db.audit(actor, "import_statement", "bank_statement", statement_id,
                          "%s; %d rows; unit=%s" % (file_name or "", len(prepared), unit), con)
        return {"statement_id": statement_id, "duplicate": False, "status": "preview",
                "checksum": checksum, "rows": prepared, "errors": errors}

    def commit_statement(self, statement_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM bank_statements WHERE id=?", (statement_id,)).fetchone()
            if not row:
                raise ValidationError("گردش بانکی یافت نشد.")
            if row["status"] == "committed":
                return True
            con.execute("UPDATE bank_statements SET status='committed' WHERE id=?",
                        (statement_id,))
            self.db.audit(actor, "commit_statement", "bank_statement", statement_id, "", con)
            return True

    def list_statements(self, limit=100):
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(
                """SELECT s.*, b.code AS bank_code FROM bank_statements s
                   JOIN bank_accounts b ON b.id=s.bank_account_id
                   ORDER BY s.id DESC LIMIT ?""", (int(limit),)).fetchall()]

    def list_transactions(self, statement_id=None, status=None, limit=500):
        sql = "SELECT t.*, s.file_name FROM bank_transactions t JOIN bank_statements s ON s.id=t.statement_id"
        params = []
        if statement_id:
            sql += " WHERE t.statement_id=?"
            params.append(statement_id)
        elif status:
            sql += " WHERE t.status=?"
            params.append(status)
        sql += " ORDER BY t.transaction_date, t.id LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    # -- reconciliation ----------------------------------------------------- #
    def suggest_matches(self, transaction_id):
        """Suggest documents that could explain a bank transaction."""
        with self.db.reader() as con:
            tx = con.execute("SELECT * FROM bank_transactions WHERE id=?",
                             (transaction_id,)).fetchone()
            if not tx:
                raise ValidationError("تراکنش یافت نشد.")
            if tx["direction"] == "in":
                sql = """SELECT id, code, amount_rial, payment_date AS doc_date FROM payments
                         WHERE direction='in' AND amount_rial=? AND posted_entry_id IS NULL"""
            else:
                sql = """SELECT id, code, amount_rial, payment_date AS doc_date FROM payments
                         WHERE direction='out' AND amount_rial=? AND posted_entry_id IS NULL"""
            candidates = con.execute(sql, (int(tx["amount_rial"]),)).fetchall()
            invoices = con.execute(
                """SELECT id, code, amount_rial, document_date AS doc_date FROM invoices
                   WHERE amount_rial=? AND status='قطعی' AND posted_entry_id IS NULL""",
                (int(tx["amount_rial"]),)).fetchall()
        suggestions = []
        tx_date = date.fromisoformat(tx["transaction_date"])
        for row in list(candidates) + list(invoices):
            try:
                doc_date = date.fromisoformat(row["doc_date"])
            except ValueError:
                continue
            delta = abs((doc_date - tx_date).days)
            confidence = 1.0 if delta == 0 else (0.9 if delta <= 2 else (0.7 if delta <= 7 else 0.4))
            suggestions.append({"target_type": "payment" if row in candidates else "invoice",
                                "target_id": row["id"], "code": row["code"],
                                "amount_rial": int(row["amount_rial"]),
                                "days_difference": delta, "confidence": confidence})
        suggestions.sort(key=lambda item: item["confidence"], reverse=True)
        with self.db.transaction() as con:
            for item in suggestions:
                con.execute(
                    """INSERT OR REPLACE INTO bank_matches(transaction_id, target_type, target_id,
                            confidence, status, note, created_at)
                       VALUES(?,?,?,?, 'suggested', ?, ?)""",
                    (transaction_id, item["target_type"], item["target_id"],
                     item["confidence"], "اختلاف %d روز" % item["days_difference"], now_iso()))
        return suggestions

    def accept_match(self, match_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM bank_matches WHERE id=?", (match_id,)).fetchone()
            if not row:
                raise ValidationError("تطابق یافت نشد.")
            if row["status"] == "accepted":
                return True
            con.execute(
                "UPDATE bank_matches SET status='accepted', decided_by=?, decided_at=? WHERE id=?",
                (actor, now_iso(), match_id))
            con.execute(
                """UPDATE bank_transactions SET status='matched', matched_type=?, matched_id=?
                   WHERE id=?""",
                (row["target_type"], row["target_id"], row["transaction_id"]))
            self.db.audit(actor, "accept_match", "bank_transaction", row["transaction_id"],
                          "%s=%s" % (row["target_type"], row["target_id"]), con)
            return True

    def reject_match(self, match_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM bank_matches WHERE id=?", (match_id,)).fetchone()
            if not row:
                raise ValidationError("تطابق یافت نشد.")
            con.execute(
                "UPDATE bank_matches SET status='rejected', decided_by=?, decided_at=? WHERE id=?",
                (actor, now_iso(), match_id))
            self.db.audit(actor, "reject_match", "bank_transaction", row["transaction_id"], "", con)
            return True

    # -- payments ----------------------------------------------------------- #
    def create_payment(self, party_id, direction, amount_rial, payment_date=None,
                       method="bank", bank_account_id=None, cheque_id=None, note="",
                       source_type=None, source_id=None, unit="ریال", actor="کاربر محلی"):
        if direction not in DIRECTIONS:
            raise ValidationError("جهت پرداخت نامعتبر است.")
        amount = to_rial(amount_rial, unit, "مبلغ")
        if amount <= 0:
            raise ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        stamp = now_iso()
        payment_date = normalize_iso_date(payment_date or stamp[:10], "تاریخ پرداخت")
        with self.db.transaction() as con:
            if not con.execute("SELECT 1 FROM parties WHERE id=?", (party_id,)).fetchone():
                raise ValidationError("طرف حساب وجود ندارد.")
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM payments").fetchone()
            code = "PAY-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO payments(code, party_id, direction, amount_rial, method,
                        payment_date, bank_account_id, cheque_id, source_type, source_id, note,
                        created_at, created_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, party_id, direction, amount, method, payment_date, bank_account_id,
                 cheque_id, source_type, str(source_id) if source_id else None,
                 str(note or "").strip() or None, stamp, actor))
            self.db.audit(actor, "create", "payment", cur.lastrowid,
                          "%s; %s %d rial" % (code, direction, amount), con)
            return cur.lastrowid

    def list_payments(self, party_id=None, direction=None, limit=200):
        sql = "SELECT p.*, b.display_name AS party_name FROM payments p JOIN parties b ON b.id=p.party_id"
        params = []
        if party_id:
            sql += " WHERE p.party_id=?"
            params.append(party_id)
        elif direction:
            sql += " WHERE p.direction=?"
            params.append(direction)
        sql += " ORDER BY p.id DESC LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    # -- cheques ------------------------------------------------------------ #
    def create_cheque(self, cheque_type, party_id, amount_rial, issue_date=None, due_date=None,
                      bank_account_id=None, note="", unit="ریال", actor="کاربر محلی"):
        if cheque_type not in ("received", "issued"):
            raise ValidationError("نوع چک نامعتبر است.")
        amount = to_rial(amount_rial, unit, "مبلغ چک")
        if amount <= 0:
            raise ValidationError("مبلغ چک باید بزرگ‌تر از صفر باشد.")
        stamp = now_iso()
        issue_date = normalize_iso_date(issue_date or stamp[:10], "تاریخ صدور")
        due_date = normalize_iso_date(due_date or stamp[:10], "تاریخ سررسید")
        with self.db.transaction() as con:
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM cheques").fetchone()
            code = "CHQ-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO cheques(code, cheque_type, party_id, amount_rial, issue_date,
                        due_date, status, bank_account_id, note, created_at, created_by)
                   VALUES(?,?,?,?,?,?, 'issued', ?,?,?,?)""",
                (code, cheque_type, party_id, amount, issue_date, due_date, bank_account_id,
                 str(note or "").strip() or None, stamp, actor))
            self._event(con, cur.lastrowid, "issued", actor, amount, "صدور چک")
            self.db.audit(actor, "create", "cheque", cur.lastrowid,
                          "%s; %s %d rial" % (code, cheque_type, amount), con)
            return cur.lastrowid

    def _event(self, con, cheque_id, event_type, actor, amount_rial=None, note=None):
        con.execute(
            """INSERT INTO cheque_events(cheque_id, event_type, event_at, actor, amount_rial, note)
               VALUES(?,?,?,?,?,?)""",
            (cheque_id, event_type, now_iso(), actor, amount_rial, note))

    def cheque_event(self, cheque_id, event_type, actor="کاربر محلی", note="", amount_rial=None):
        """Record a cheque lifecycle event (send to bank, return, ...)."""
        allowed = {"in_process", "bounced", "cancelled", "cleared"}
        if event_type not in allowed:
            raise ValidationError("رویداد چک نامعتبر است: %s" % event_type)
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM cheques WHERE id=?", (cheque_id,)).fetchone()
            if not row:
                raise ValidationError("چک یافت نشد.")
            if row["status"] == "cleared":
                raise ConflictError("چک تسویه‌شده قابل تغییر وضعیت نیست.")
            con.execute("UPDATE cheques SET status=? WHERE id=?", (event_type, cheque_id))
            self._event(con, cheque_id, event_type, actor, amount_rial, note)
            self.db.audit(actor, event_type, "cheque", cheque_id, note or "", con)
            return True

    def clear_cheque(self, cheque_id, clear_date=None, bank_account_id=None, actor="کاربر محلی",
                     ledger=None):
        """Clear a cheque and post the related movement to the ledger."""
        with self.db.reader() as con:
            row = con.execute("SELECT * FROM cheques WHERE id=?", (cheque_id,)).fetchone()
        if not row:
            raise ValidationError("چک یافت نشد.")
        if row["status"] == "cleared":
            raise ConflictError("این چک قبلاً تسویه شده است.")
        amount = int(row["amount_rial"])
        if ledger is None:
            from .ledger import LedgerService

            ledger = LedgerService(self.db)
        cash_account = "1010" if (bank_account_id or row["bank_account_id"]) else "1000"
        if row["cheque_type"] == "received":
            lines = [
                {"account_code": cash_account, "debit_rial": amount, "credit_rial": 0,
                 "description": "وصول چک"},
                {"account_code": "1100", "debit_rial": 0, "credit_rial": amount,
                 "description": "وصول چک دریافتی", "party_ref": str(row["party_id"])},
            ]
            label = "وصول چک دریافتی"
        else:
            lines = [
                {"account_code": "2000", "debit_rial": amount, "credit_rial": 0,
                 "description": "پرداخت چک", "party_ref": str(row["party_id"])},
                {"account_code": cash_account, "debit_rial": 0, "credit_rial": amount,
                 "description": "پرداخت چک صادره"},
            ]
            label = "پرداخت چک صادره"
        clear_date = normalize_iso_date(clear_date or now_iso()[:10], "تاریخ وصول/پرداخت")
        entry_id, created = ledger._post(clear_date, "%s - %s" % (label, row["code"]),
                                         lines, "cheque", cheque_id, actor)
        with self.db.transaction() as con:
            con.execute("UPDATE cheques SET status='cleared', cleared_entry_id=? WHERE id=?",
                        (entry_id, cheque_id))
            self._event(con, cheque_id, "cleared", actor, amount, "تسویه چک")
            self.db.audit(actor, "clear", "cheque", cheque_id,
                          "entry=%s amount=%d rial" % (entry_id, amount), con)
        return {"entry_id": entry_id, "created": created, "amount_rial": amount}

    def list_cheques(self, status=None, cheque_type=None, limit=200):
        sql = "SELECT c.*, p.display_name AS party_name FROM cheques c LEFT JOIN parties p ON p.id=c.party_id"
        params = []
        if status:
            sql += " WHERE c.status=?"
            params.append(status)
        elif cheque_type:
            sql += " WHERE c.cheque_type=?"
            params.append(cheque_type)
        sql += " ORDER BY c.due_date, c.id LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def cheques_due(self, within_days=7, as_of=None):
        """Cheques whose due date is close - the daily working list."""
        as_of = normalize_iso_date(as_of or now_iso()[:10], "تاریخ")
        limit_date = (date.fromisoformat(as_of) + timedelta(days=int(within_days))).isoformat()
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT c.*, p.display_name AS party_name FROM cheques c
                   LEFT JOIN parties p ON p.id=c.party_id
                   WHERE c.status IN ('issued','in_process') AND c.due_date <= ?
                   ORDER BY c.due_date""", (limit_date,)).fetchall()
        return [dict(r) for r in rows]
