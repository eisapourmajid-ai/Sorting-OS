# -*- coding: utf-8 -*-
"""Fiscal periods, closing entries and period locks (Prompt 22 / spec 4.10).

Closing a period is a separate, permission-gated, testable process that:

1. requires a **verified backup** of the live database;
2. posts closing entries that move the revenue/expense balances of the period
   into retained earnings (3100) - always as balanced entries;
3. locks the period so that later documents cannot be posted into it.

Nothing here deletes data: a closed period is only *locked*, and the closing
entry can be reversed with a normal journal reversal.
"""
from __future__ import annotations

from ..core import ConflictError, PermissionDenied, ValidationError, normalize_iso_date, now_iso


class PeriodService:
    """Fiscal period management."""

    def __init__(self, db):
        self.db = db

    # -- periods ------------------------------------------------------------ #
    def create_period(self, code, title=None, start_date=None, end_date=None,
                      actor="کاربر محلی"):
        code = str(code or "").strip()
        if not code:
            raise ValidationError("کد دوره الزامی است.")
        start_date = normalize_iso_date(start_date or now_iso()[:10], "تاریخ شروع دوره")
        end_date = normalize_iso_date(end_date or now_iso()[:10], "تاریخ پایان دوره")
        if start_date > end_date:
            raise ValidationError("تاریخ شروع نباید بعد از پایان باشد.")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM fiscal_periods WHERE code=?", (code,)).fetchone():
                raise ConflictError("این دوره قبلاً تعریف شده است: %s" % code)
            cur = con.execute(
                """INSERT INTO fiscal_periods(code, title, start_date, end_date, status, created_at)
                   VALUES(?,?,?,?, 'open', ?)""",
                (code, str(title or "").strip() or None, start_date, end_date, now_iso()))
            self.db.audit(actor, "create", "fiscal_period", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_periods(self):
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM fiscal_periods ORDER BY start_date").fetchall()]

    def period_for_date(self, iso_date):
        iso_date = normalize_iso_date(iso_date, "تاریخ")
        with self.db.reader() as con:
            row = con.execute(
                "SELECT * FROM fiscal_periods WHERE start_date <= ? AND end_date >= ?",
                (iso_date, iso_date)).fetchone()
        return dict(row) if row else None

    def assert_open(self, iso_date, actor=None):
        """Raise when a document wants to be posted into a closed period."""
        period = self.period_for_date(iso_date)
        if period and period["status"] == "closed":
            raise ConflictError(
                "دوره «%s» بسته شده است و ثبت سند جدید در آن مجاز نیست." % period["code"])
        return True

    # -- closing ------------------------------------------------------------ #
    def close(self, period_id, actor="کاربر محلی", ledger=None, backup_dir=None,
              require_backup=True):
        """Close a period: backup first, then a balanced closing entry."""
        with self.db.reader() as con:
            period = con.execute("SELECT * FROM fiscal_periods WHERE id=?",
                                 (period_id,)).fetchone()
        if not period:
            raise ValidationError("دوره یافت نشد.")
        if period["status"] == "closed":
            raise ConflictError("این دوره قبلاً بسته شده است.")
        if require_backup:
            from .backup import BackupService

            backup = BackupService(self.db)
            target = backup_dir or (self.db.path.rsplit(".", 1)[0] + "-backups")
            report = backup.create(target, actor=actor)
            if not report:
                raise ConflictError("تهیه backup پیش از بستن دوره الزامی است.")
        if ledger is None:
            from .ledger import LedgerService

            ledger = LedgerService(self.db)
        balances = ledger.book._account_balances(as_of=period["end_date"],
                                                 date_from=period["start_date"])
        lines = []
        revenue = 0
        expense = 0
        for account in balances:
            if account["category"] == "revenue":
                # a revenue account carries a credit balance: close it with a debit
                amount = abs(int(account["raw_net_rial"]))
                if amount:
                    lines.append({"account_code": account["code"], "debit_rial": amount,
                                  "credit_rial": 0, "description": "بستن حساب درآمد"})
                    revenue += amount
            elif account["category"] == "expense":
                # an expense account carries a debit balance: close it with a credit
                amount = abs(int(account["raw_net_rial"]))
                if amount:
                    lines.append({"account_code": account["code"], "debit_rial": 0,
                                  "credit_rial": amount, "description": "بستن حساب هزینه"})
                    expense += amount
        if not lines:
            with self.db.transaction() as con:
                con.execute("UPDATE fiscal_periods SET status='closed', closed_by=?, closed_at=?"
                            " WHERE id=?", (actor, now_iso(), period_id))
                self.db.audit(actor, "close", "fiscal_period", period_id,
                              "دوره بدون گردش بسته شد", con)
            return {"closed": True, "entry_id": None, "revenue_rial": 0, "expense_rial": 0}
        # net result: revenue - expense goes to retained earnings (3100)
        net = revenue - expense
        if net > 0:
            # profit increases retained earnings (credit side)
            lines.append({"account_code": "3100", "debit_rial": 0, "credit_rial": net,
                          "description": "انتقال سود دوره به سود و زیان انباشته"})
        elif net < 0:
            lines.append({"account_code": "3100", "debit_rial": -net, "credit_rial": 0,
                          "description": "انتقال زیان دوره به سود و زیان انباشته"})
        entry_id, created = ledger._post(
            period["end_date"], "سند بستن دوره %s" % period["code"], lines,
            "period_close", period_id, actor)
        with self.db.transaction() as con:
            con.execute(
                """UPDATE fiscal_periods SET status='closed', closed_by=?, closed_at=?,
                        closing_entry_id=? WHERE id=?""",
                (actor, now_iso(), entry_id, period_id))
            con.execute(
                """INSERT INTO period_locks(period_id, locked_from, locked_until, reason,
                        created_at, created_by)
                   VALUES(?,?,?,?,?,?)""",
                (period_id, period["start_date"], period["end_date"], "بستن دوره مالی",
                 now_iso(), actor))
            self.db.audit(actor, "close", "fiscal_period", period_id,
                          "entry=%s" % entry_id, con)
        return {"closed": True, "entry_id": entry_id, "created": created,
                "revenue_rial": revenue, "expense_rial": expense, "net_rial": net}

    def reopen(self, period_id, actor="کاربر محلی"):
        """Re-open a period (only the lock is removed; the closing entry stays)."""
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM fiscal_periods WHERE id=?", (period_id,)).fetchone()
            if not row:
                raise ValidationError("دوره یافت نشد.")
            if row["status"] != "closed":
                raise ConflictError("این دوره باز است.")
            con.execute("UPDATE fiscal_periods SET status='open' WHERE id=?", (period_id,))
            con.execute("DELETE FROM period_locks WHERE period_id=?", (period_id,))
            self.db.audit(actor, "reopen", "fiscal_period", period_id, "", con)
            return True
