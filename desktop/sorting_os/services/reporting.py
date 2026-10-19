# -*- coding: utf-8 -*-
"""Reporting and KPI dashboard (Prompt 22).

Every number in this module is read from the database - there is no mock or
hard-coded figure.  Financial figures come from the posted journal, and
operational figures come from the operational tables; the two are never mixed.

Every report states its money unit explicitly and, where a mapping is still
provisional (cash-flow classification, current/non-current split), it says so
instead of pretending the number is final.
"""
from __future__ import annotations

from decimal import Decimal

from ..core import format_money, normalize_iso_date, now_iso


class ReportService:
    """Financial, operational and management reports."""

    def __init__(self, db, book=None):
        self.db = db
        if book is None:
            from accounting_core import AccountingBook

            book = AccountingBook(db.path)
        self.book = book

    # -- dashboard ---------------------------------------------------------- #
    def dashboard(self, as_of=None):
        """KPI dashboard built from real data."""
        as_of = normalize_iso_date(as_of or now_iso()[:10], "تاریخ گزارش")
        with self.db.reader() as con:
            parties = con.execute("SELECT COUNT(*) FROM parties WHERE is_active=1").fetchone()[0]
            open_shipments = con.execute(
                "SELECT COUNT(*) FROM shipments WHERE current_state NOT IN ('closed','dispatched')"
            ).fetchone()[0]
            received_today = con.execute(
                "SELECT COALESCE(SUM(received_weight),0) FROM shipments WHERE received_at=?",
                (as_of,)).fetchone()[0]
            drafts = con.execute(
                "SELECT COUNT(*) FROM invoices WHERE status='پیش‌نویس'").fetchone()[0]
            confirmed = con.execute(
                "SELECT COUNT(*) FROM invoices WHERE status='قطعی' AND amount_rial IS NOT NULL"
            ).fetchone()[0]
            draft_amount = con.execute(
                """SELECT COALESCE(SUM(amount_rial),0) FROM invoices
                   WHERE status='پیش‌نویس' AND amount_rial IS NOT NULL""").fetchone()[0]
            confirmed_amount = con.execute(
                """SELECT COALESCE(SUM(amount_rial),0) FROM invoices
                   WHERE status='قطعی' AND amount_rial IS NOT NULL""").fetchone()[0]
            receivables = con.execute(
                """SELECT COALESCE(SUM(l.debit_rial - l.credit_rial),0)
                   FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                   WHERE l.account_code='1100' AND e.status='posted'""").fetchone()[0]
            payables = con.execute(
                """SELECT COALESCE(SUM(l.credit_rial - l.debit_rial),0)
                   FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                   WHERE l.account_code='2000' AND e.status='posted'""").fetchone()[0]
            stock = con.execute(
                """SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN weight_kg ELSE 0 END),0)
                          - COALESCE(SUM(CASE WHEN movement_type='out' THEN weight_kg ELSE 0 END),0)
                   FROM inventory_transactions WHERE status='posted'""").fetchone()[0]
            unmatched = con.execute(
                "SELECT COUNT(*) FROM bank_transactions WHERE status='unmatched'").fetchone()[0]
            due_cheques = con.execute(
                "SELECT COUNT(*) FROM cheques WHERE status IN ('issued','in_process')"
            ).fetchone()[0]
            pending_settlements = con.execute(
                "SELECT COUNT(*) FROM settlements WHERE status='draft'").fetchone()[0]
        return {
            "as_of": as_of,
            "money_unit": "ریال",
            "operational": {
                "active_parties": parties,
                "open_shipments": open_shipments,
                "received_weight_today_kg": float(received_today),
                "stock_balance_kg": float(stock),
                "pending_settlements": pending_settlements,
            },
            "commercial": {
                "draft_invoices": drafts,
                "draft_amount_rial": int(draft_amount),
                "confirmed_invoices": confirmed,
                "confirmed_amount_rial": int(confirmed_amount),
                "unmatched_bank_transactions": unmatched,
                "open_cheques": due_cheques,
            },
            "financial": {
                "receivables_rial": int(receivables),
                "payables_rial": int(payables),
                "receivables_display": format_money(int(receivables), "تومان"),
                "payables_display": format_money(int(payables), "تومان"),
            },
        }

    # -- financial reports -------------------------------------------------- #
    def financial(self, date_from, date_to, unit="تومان"):
        """The four base statements, all built from posted journal lines."""
        date_from = normalize_iso_date(date_from, "از تاریخ")
        date_to = normalize_iso_date(date_to, "تا تاریخ")
        trial = self.book.trial_balance(date_from, date_to)
        balance = self.book.balance_sheet(date_to)
        income = self.book.income_statement(date_from, date_to)
        cash = self.book.cash_flow_statement(date_from, date_to)
        return {
            "period": {"date_from": date_from, "date_to": date_to},
            "money_unit": unit,
            "trial_balance": trial,
            "balance_sheet": balance,
            "income_statement": income,
            "cash_flow": cash,
            "notes": [
                "گردش نقدی بر اساس نگاشت cash_flow_class حساب‌های مقابل است و تا تأیید حسابدار "
                "(DEC-012) ماهیت مدیریتی دارد.",
                "تفکیک جاری/غیرجاری در نسبت‌ها بر پایه پیشوند کد حساب است و باید با فلگ سرفصل‌ها "
                "جایگزین شود.",
            ],
        }

    def ratios(self, as_of, period_from, period_to):
        result = dict(self.book.financial_ratios(
            normalize_iso_date(as_of, "تا تاریخ"),
            normalize_iso_date(period_from, "از تاریخ"),
            normalize_iso_date(period_to, "تا تاریخ")))
        for key in ("current_ratio", "liabilities_to_assets", "net_profit_margin"):
            value = result.get(key)
            result[key] = float(value) if isinstance(value, Decimal) else value
        result["status"] = "provisional"
        return result

    def account_ledger(self, account_code, date_from=None, date_to=None):
        return self.book.account_ledger(account_code, date_from, date_to)

    def party_statement(self, party_id, date_from=None, date_to=None):
        from .ledger import LedgerService

        return LedgerService(self.db, self.book).party_subledger(party_id, date_from, date_to)

    # -- operational reports ------------------------------------------------ #
    def operations_report(self, date_from, date_to):
        """Throughput, sorting yield and dispatch statistics for a period."""
        date_from = normalize_iso_date(date_from, "از تاریخ")
        date_to = normalize_iso_date(date_to, "تا تاریخ")
        with self.db.reader() as con:
            received = con.execute(
                """SELECT COALESCE(SUM(received_weight),0) AS kg, COUNT(*) AS cnt
                   FROM shipments WHERE received_at BETWEEN ? AND ?""",
                (date_from, date_to)).fetchone()
            sorting = con.execute(
                """SELECT COALESCE(SUM(input_weight_kg),0) AS input_kg,
                          COALESCE(SUM(waste_weight_kg),0) AS waste_kg,
                          COALESCE(SUM(loss_weight_kg),0) AS loss_kg,
                          COALESCE(SUM(difference_weight_kg),0) AS diff_kg,
                          COUNT(*) AS cnt
                   FROM sorting_operations
                   WHERE status='confirmed' AND measured_at BETWEEN ? AND ?""",
                (date_from, date_to)).fetchone()
            output = con.execute(
                """SELECT COALESCE(SUM(l.weight_kg),0) AS output_kg
                   FROM sorting_output_lines l JOIN sorting_operations o ON o.id=l.operation_id
                   WHERE o.status='confirmed' AND o.measured_at BETWEEN ? AND ?
                     AND l.line_type='output'""",
                (date_from, date_to)).fetchone()
            dispatched = con.execute(
                """SELECT COALESCE(SUM(l.weight_kg),0) AS kg, COUNT(DISTINCT l.dispatch_id) AS cnt
                   FROM dispatch_lines l JOIN dispatches d ON d.id=l.dispatch_id
                   WHERE d.status='confirmed' AND d.dispatched_at BETWEEN ? AND ?""",
                (date_from, date_to)).fetchone()
            by_product = con.execute(
                """SELECT p.name AS product, COALESCE(SUM(l.weight_kg),0) AS kg
                   FROM dispatch_lines l JOIN dispatches d ON d.id=l.dispatch_id
                   LEFT JOIN products p ON p.id=l.product_id
                   WHERE d.status='confirmed' AND d.dispatched_at BETWEEN ? AND ?
                   GROUP BY p.name ORDER BY kg DESC""",
                (date_from, date_to)).fetchall()
        input_kg = float(sorting["input_kg"])
        output_kg = float(output["output_kg"])
        waste_kg = float(sorting["waste_kg"])
        return {
            "period": {"date_from": date_from, "date_to": date_to},
            "received": {"shipments": int(received["cnt"]), "weight_kg": float(received["kg"])},
            "sorting": {
                "operations": int(sorting["cnt"]),
                "input_kg": input_kg,
                "output_kg": output_kg,
                "waste_kg": waste_kg,
                "loss_kg": float(sorting["loss_kg"]),
                "difference_kg": float(sorting["diff_kg"]),
                "output_ratio": (output_kg / input_kg) if input_kg else None,
                "waste_ratio": (waste_kg / input_kg) if input_kg else None,
            },
            "dispatch": {"orders": int(dispatched["cnt"]), "weight_kg": float(dispatched["kg"])},
            "dispatch_by_product": [dict(r) for r in by_product],
        }

    def inventory_report(self):
        from .operations import OperationsService

        return OperationsService(self.db).inventory_balance()

    # -- receivables -------------------------------------------------------- #
    def receivables_aging(self, as_of=None):
        """Ageing of confirmed invoices that are not settled yet.

        Receipts are allocated to the invoices of the same party in FIFO order
        (document_date, then id). The allocation policy is registered as open
        decision DEC-015 until the business confirms it.
        """
        as_of = normalize_iso_date(as_of or now_iso()[:10], "تاریخ")
        with self.db.reader() as con:
            invoices = con.execute(
                """SELECT i.id, i.code, i.party_id, i.document_date, i.due_date,
                          i.amount_rial, p.display_name
                   FROM invoices i JOIN parties p ON p.id=i.party_id
                   WHERE i.status='قطعی' AND i.amount_rial IS NOT NULL
                   ORDER BY i.party_id, i.document_date, i.id""").fetchall()
            receipts = con.execute(
                """SELECT party_id, COALESCE(SUM(amount_rial),0) AS paid FROM payments
                   WHERE direction='in' GROUP BY party_id""").fetchall()
        paid_by_party = {int(r["party_id"]): int(r["paid"]) for r in receipts}

        # FIFO allocation of the party receipts over the party invoices
        allocated = {}
        for invoice in invoices:
            party_id = int(invoice["party_id"])
            remaining = paid_by_party.get(party_id, 0)
            already = allocated.get(party_id, 0)
            available = max(remaining - already, 0)
            amount = int(invoice["amount_rial"])
            paid = min(amount, available)
            allocated[party_id] = already + paid

        buckets = {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "over_90": 0}
        rows = []
        from datetime import date as _date

        today = _date.fromisoformat(as_of)
        for invoice in invoices:
            amount = int(invoice["amount_rial"])
            party_id = int(invoice["party_id"])
            paid = allocated.get(party_id, 0)
            outstanding = max(amount - paid, 0)
            allocated[party_id] = paid + max(amount - paid - outstanding, 0)
            rows.append({"id": invoice["id"], "code": invoice["code"],
                         "party_id": party_id, "display_name": invoice["display_name"],
                         "document_date": invoice["document_date"],
                         "due_date": invoice["due_date"], "amount_rial": amount,
                         "outstanding_rial": outstanding})
        for row in rows:
            outstanding = row["outstanding_rial"]
            if outstanding <= 0:
                row["bucket"] = "settled"
                continue
            due = row["due_date"]
            if not due:
                row["bucket"] = "current"
                buckets["current"] += outstanding
                continue
            days = (today - _date.fromisoformat(due)).days
            if days <= 0:
                row["bucket"] = "current"
                buckets["current"] += outstanding
            elif days <= 30:
                row["bucket"] = "1_30"
                buckets["1_30"] += outstanding
            elif days <= 60:
                row["bucket"] = "31_60"
                buckets["31_60"] += outstanding
            elif days <= 90:
                row["bucket"] = "61_90"
                buckets["61_90"] += outstanding
            else:
                row["bucket"] = "over_90"
                buckets["over_90"] += outstanding
        return {"as_of": as_of, "money_unit": "ریال", "allocation_policy":
                "receipts-fifo-v1 (DEC-015)", "buckets": buckets, "items": rows,
                "total_outstanding_rial": sum(buckets.values())}

    def party_receivables(self):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT id, display_name, balance FROM (
                        SELECT p.id AS id, p.display_name AS display_name,
                               COALESCE(l.balance, 0) AS balance
                        FROM parties p
                        LEFT JOIN (
                             SELECT l.party_ref AS pref,
                                    SUM(l.debit_rial - l.credit_rial) AS balance
                             FROM journal_lines l
                             JOIN journal_entries e ON e.id = l.entry_id
                             WHERE e.status='posted' AND l.party_ref IS NOT NULL
                             GROUP BY l.party_ref
                        ) l ON l.pref = CAST(p.id AS TEXT)
                        WHERE p.is_active=1
                   ) WHERE balance <> 0 ORDER BY balance DESC""").fetchall()
        return [{"party_id": int(r["id"]), "name": r["display_name"],
                 "balance_rial": int(r["balance"])} for r in rows]
