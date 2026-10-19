# -*- coding: utf-8 -*-
"""Auditable, offline-first double-entry accounting core for SORTING OS.

Money is stored as integer Iranian rials. Toman is a presentation/input unit only.
This module intentionally does not auto-post legacy invoice rows: their historic
currency semantics and posting rules must be approved before any migration.
Python 3.8+; standard library only.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

SCHEMA_VERSION = 1

DEFAULT_ACCOUNTS = [
    # code, name, category, natural_side, cash_flow_class, is_cash
    ("1000", "صندوق", "asset", "debit", "operating", 1),
    ("1010", "بانک‌ها", "asset", "debit", "operating", 1),
    ("1100", "حساب‌های دریافتنی", "asset", "debit", "operating", 0),
    ("1200", "موجودی کالای متعلق به مجموعه", "asset", "debit", "operating", 0),
    ("1300", "پیش‌پرداخت‌ها و سپرده‌ها", "asset", "debit", "operating", 0),
    ("1500", "دارایی ثابت", "asset", "debit", "investing", 0),
    ("1590", "استهلاک انباشته دارایی ثابت", "asset", "credit", "investing", 0),
    ("2000", "حساب‌های پرداختنی", "liability", "credit", "operating", 0),
    ("2100", "تسهیلات و بدهی‌های مالی", "liability", "credit", "financing", 0),
    ("2200", "مالیات و عوارض پرداختنی", "liability", "credit", "operating", 0),
    ("3000", "سرمایه", "equity", "credit", "financing", 0),
    ("3100", "سود و زیان انباشته سنواتی", "equity", "credit", "financing", 0),
    ("4000", "درآمد فروش و خدمات", "revenue", "credit", "operating", 0),
    ("4100", "سایر درآمدها", "revenue", "credit", "operating", 0),
    ("5000", "بهای تمام‌شده کالای فروش‌رفته", "expense", "debit", "operating", 0),
    ("6000", "هزینه‌های عملیاتی", "expense", "debit", "operating", 0),
    ("6100", "کارمزد و هزینه خدمات بانکی", "expense", "debit", "operating", 0),
    ("6200", "ضایعات و کسری تأییدشده", "expense", "debit", "operating", 0),
    ("6300", "هزینه استهلاک", "expense", "debit", "operating", 0),
]

CATEGORIES = {"asset", "liability", "equity", "revenue", "expense"}
SIDES = {"debit", "credit"}
FLOW_CLASSES = {"operating", "investing", "financing", "other"}


def normalize_digits(value):
    """Convert Persian/Arabic digits and common separators to stable ASCII text."""
    if value is None:
        return ""
    text = str(value).strip()
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return text.translate(table)


def _integer_rial(value, field="مبلغ ریالی"):
    """Accept only integral numeric values; never silently truncate money."""
    if isinstance(value, bool):
        raise ValueError("%s باید عدد صحیح ریال باشد." % field)
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError):
        raise ValueError("%s معتبر نیست." % field)
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError("%s باید عدد صحیح ریال باشد؛ گردکردن خودکار ممنوع است." % field)
    return int(amount)


def parse_amount_to_rial(raw, unit="ریال"):
    """Parse a non-negative amount and return integer rials without float math.

    Supported units: ریال / rial / تومان / toman. Decimal input is accepted only
    when conversion yields a whole rial; for example 12.5 toman = 125 rials.
    """
    text = normalize_digits(raw).replace("٬", "").replace(",", "").replace("،", "")
    text = re.sub(r"\s+", "", text)
    for token in ("ریال", "ريال", "تومان", "rial", "rials", "toman", "tomans"):
        text = text.replace(token, "")
    if not text:
        raise ValueError("مبلغ خالی است.")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError("قالب مبلغ معتبر نیست.")
    if not amount.is_finite() or amount < 0:
        raise ValueError("مبلغ باید عددی متناهی و غیرمنفی باشد.")
    u = normalize_digits(unit).strip().lower()
    if u in ("تومان", "tomān", "toman", "tomans"):
        amount *= Decimal(10)
    elif u not in ("ریال", "ريال", "rial", "rials"):
        raise ValueError("واحد ورودی باید ریال یا تومان باشد.")
    if amount != amount.to_integral_value():
        raise ValueError("مبلغ پس از تبدیل باید به ریال صحیح برسد؛ مقدار اعشاریِ کمتر از یک ریال پذیرفته نیست.")
    return int(amount)


def format_money(amount_rial, unit="تومان", local_digits=False):
    """Render integer rials exactly in a requested display unit, with no rounding."""
    n = _integer_rial(amount_rial)
    u = normalize_digits(unit).strip().lower()
    if u in ("ریال", "ريال", "rial", "rials"):
        divisor, label = Decimal(1), "ریال"
    elif u in ("تومان", "toman", "tomans"):
        divisor, label = Decimal(10), "تومان"
    elif u in ("میلیون تومان", "million toman", "million tomans"):
        divisor, label = Decimal(10000000), "میلیون تومان"
    else:
        raise ValueError("واحد نمایش باید ریال، تومان یا میلیون تومان باشد.")
    value = Decimal(n) / divisor
    rendered = format(value, ",f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if local_digits:
        rendered = rendered.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    return rendered + " " + label


def _iso_date(value, field="تاریخ"):
    if not value:
        raise ValueError("%s الزامی است؛ قالب داخلی تاریخ YYYY-MM-DD است." % field)
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        raise ValueError("%s باید با قالب YYYY-MM-DD وارد شود." % field)
    return parsed.strftime("%Y-%m-%d")


class _ClosingConnection(sqlite3.Connection):
    """SQLite context manager that also closes the connection on exit."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class AccountingBook:
    """SQLite-backed append-only posted journal and financial reporting service."""

    def __init__(self, db_path):
        self.path = db_path
        self._initialize()

    def connect(self):
        con = sqlite3.connect(self.path, timeout=15, factory=_ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=15000")
        return con

    def _initialize(self):
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS accounting_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS accounting_accounts (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('asset','liability','equity','revenue','expense')),
                    normal_side TEXT NOT NULL CHECK(normal_side IN ('debit','credit')),
                    cash_flow_class TEXT NOT NULL DEFAULT 'operating'
                        CHECK(cash_flow_class IN ('operating','investing','financing','other')),
                    is_cash INTEGER NOT NULL DEFAULT 0 CHECK(is_cash IN (0,1)),
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_no TEXT NOT NULL UNIQUE,
                    entry_date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source_type TEXT,
                    source_id TEXT,
                    status TEXT NOT NULL DEFAULT 'posted' CHECK(status='posted'),
                    actor TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reverses_entry_id INTEGER UNIQUE REFERENCES journal_entries(id),
                    UNIQUE(source_type, source_id)
                );
                CREATE TABLE IF NOT EXISTS journal_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL REFERENCES journal_entries(id),
                    line_no INTEGER NOT NULL,
                    account_code TEXT NOT NULL REFERENCES accounting_accounts(code),
                    description TEXT NOT NULL DEFAULT '',
                    debit_rial INTEGER NOT NULL DEFAULT 0 CHECK(debit_rial >= 0),
                    credit_rial INTEGER NOT NULL DEFAULT 0 CHECK(credit_rial >= 0),
                    party_ref TEXT,
                    cost_center TEXT,
                    CHECK ((debit_rial > 0 AND credit_rial = 0) OR
                           (credit_rial > 0 AND debit_rial = 0)),
                    UNIQUE(entry_id, line_no)
                );
                CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(entry_date, id);
                CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_code, entry_id);
                CREATE INDEX IF NOT EXISTS idx_lines_party ON journal_lines(party_ref, entry_id);
            """)
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for account in DEFAULT_ACCOUNTS:
                con.execute("""INSERT OR IGNORE INTO accounting_accounts
                    (code,name,category,normal_side,cash_flow_class,is_cash,is_active,created_at)
                    VALUES(?,?,?,?,?,?,1,?)""", account + (now,))
            con.execute("INSERT OR IGNORE INTO accounting_meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
            con.execute("INSERT OR IGNORE INTO accounting_meta(key,value) VALUES('money_base_unit','IRR')")

    def list_accounts(self, active_only=True):
        sql = "SELECT * FROM accounting_accounts"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY code"
        with self.connect() as con:
            return [dict(r) for r in con.execute(sql).fetchall()]

    def create_account(self, code, name, category, normal_side=None, cash_flow_class="operating", is_cash=False):
        code, name = str(code).strip(), str(name).strip()
        if not code or not name:
            raise ValueError("کد و نام حساب الزامی است.")
        if category not in CATEGORIES:
            raise ValueError("گروه حساب نامعتبر است.")
        if normal_side is None:
            normal_side = "debit" if category in ("asset", "expense") else "credit"
        if normal_side not in SIDES or cash_flow_class not in FLOW_CLASSES:
            raise ValueError("ماهیت حساب یا طبقه جریان نقد نامعتبر است.")
        with self.connect() as con:
            try:
                con.execute("""INSERT INTO accounting_accounts
                    (code,name,category,normal_side,cash_flow_class,is_cash,is_active,created_at)
                    VALUES(?,?,?,?,?,?,1,?)""", (code, name, category, normal_side, cash_flow_class,
                    int(bool(is_cash)), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
            except sqlite3.IntegrityError as exc:
                raise ValueError("کد حساب تکراری است یا حساب معتبر نیست: %s" % exc)
        return code

    @staticmethod
    def _normalize_lines(lines):
        cleaned = []
        for row in lines:
            account_code = str(row.get("account_code", "")).strip()
            debit = _integer_rial(row.get("debit_rial", 0) or 0, "بدهکار به ریال")
            credit = _integer_rial(row.get("credit_rial", 0) or 0, "بستانکار به ریال")
            if not account_code:
                if debit or credit:
                    raise ValueError("برای هر مبلغ باید کد حساب تعیین شود.")
                continue
            if debit < 0 or credit < 0:
                raise ValueError("مبلغ بدهکار/بستانکار نمی‌تواند منفی باشد.")
            if (debit > 0) == (credit > 0):
                raise ValueError("هر ردیف باید دقیقاً یک مبلغ مثبت در بدهکار یا بستانکار داشته باشد.")
            cleaned.append({
                "account_code": account_code,
                "debit_rial": debit,
                "credit_rial": credit,
                "description": str(row.get("description", "") or "").strip(),
                "party_ref": str(row.get("party_ref", "") or "").strip() or None,
                "cost_center": str(row.get("cost_center", "") or "").strip() or None,
            })
        if len(cleaned) < 2:
            raise ValueError("سند حسابداری باید دست‌کم دو ردیف داشته باشد.")
        debit_sum = sum(x["debit_rial"] for x in cleaned)
        credit_sum = sum(x["credit_rial"] for x in cleaned)
        if debit_sum <= 0 or debit_sum != credit_sum:
            raise ValueError("سند متوازن نیست: جمع بدهکار باید برابر جمع بستانکار و بزرگ‌تر از صفر باشد.")
        return cleaned, debit_sum

    def post_entry(self, entry_date, description, lines, actor="کاربر محلی", source_type=None,
                   source_id=None, entry_no=None, reverses_entry_id=None):
        entry_date = _iso_date(entry_date)
        description = str(description or "").strip()
        if not description:
            raise ValueError("شرح سند الزامی است.")
        clean_lines, total = self._normalize_lines(lines)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry_no = entry_no or ("JE-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing_accounts = {r[0] for r in con.execute("SELECT code FROM accounting_accounts WHERE is_active=1").fetchall()}
            missing = sorted({l["account_code"] for l in clean_lines} - existing_accounts)
            if missing:
                con.rollback()
                raise ValueError("حساب ناموجود یا غیرفعال: " + ", ".join(missing))
            if reverses_entry_id is not None:
                original = con.execute("SELECT id FROM journal_entries WHERE id=?", (int(reverses_entry_id),)).fetchone()
                if not original:
                    con.rollback()
                    raise ValueError("سند مرجع برای برگشت وجود ندارد.")
            try:
                cur = con.execute("""INSERT INTO journal_entries
                    (entry_no,entry_date,description,source_type,source_id,status,actor,created_at,reverses_entry_id)
                    VALUES(?,?,?,?,?,'posted',?,?,?)""",
                    (entry_no, entry_date, description, source_type, None if source_id is None else str(source_id),
                     actor or "کاربر محلی", stamp, reverses_entry_id))
                entry_id = cur.lastrowid
                for index, line in enumerate(clean_lines, 1):
                    con.execute("""INSERT INTO journal_lines
                        (entry_id,line_no,account_code,description,debit_rial,credit_rial,party_ref,cost_center)
                        VALUES(?,?,?,?,?,?,?,?)""", (entry_id, index, line["account_code"], line["description"],
                        line["debit_rial"], line["credit_rial"], line["party_ref"], line["cost_center"]))
                # A final database-level balance check protects against service regressions.
                sums = con.execute("SELECT SUM(debit_rial),SUM(credit_rial) FROM journal_lines WHERE entry_id=?", (entry_id,)).fetchone()
                if sums[0] != sums[1] or sums[0] != total:
                    raise ValueError("کنترل نهایی تعادل سند شکست خورد.")
                con.commit()
            except sqlite3.IntegrityError as exc:
                con.rollback()
                raise ValueError("سند تکراری یا ناسازگار است؛ ثبت دوباره انجام نشد: %s" % exc)
            except Exception:
                con.rollback()
                raise
        return entry_id

    def reverse_entry(self, entry_id, reversal_date, reason, actor="کاربر محلی"):
        reversal_date = _iso_date(reversal_date, "تاریخ برگشت")
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("علت برگشت سند الزامی است.")
        with self.connect() as con:
            header = con.execute("SELECT * FROM journal_entries WHERE id=?", (int(entry_id),)).fetchone()
            if not header:
                raise ValueError("سند پیدا نشد.")
            if header["reverses_entry_id"] is not None:
                raise ValueError("برگشتِ سند برگشتی به‌صورت خودکار مجاز نیست.")
            lines = con.execute("SELECT * FROM journal_lines WHERE entry_id=? ORDER BY line_no", (int(entry_id),)).fetchall()
        reverse_lines = [{"account_code": r["account_code"], "description": "برگشت: " + (r["description"] or ""),
                          "debit_rial": r["credit_rial"], "credit_rial": r["debit_rial"],
                          "party_ref": r["party_ref"], "cost_center": r["cost_center"]} for r in lines]
        return self.post_entry(reversal_date, "برگشت سند %s — %s" % (header["entry_no"], reason), reverse_lines,
                               actor=actor, source_type="reversal", source_id=str(entry_id),
                               reverses_entry_id=int(entry_id))

    def list_entries(self, date_from=None, date_to=None, limit=500):
        clauses, params = [], []
        if date_from:
            clauses.append("entry_date >= ?"); params.append(_iso_date(date_from, "از تاریخ"))
        if date_to:
            clauses.append("entry_date <= ?"); params.append(_iso_date(date_to, "تا تاریخ"))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self.connect() as con:
            headers = con.execute("SELECT * FROM journal_entries" + where + " ORDER BY entry_date DESC,id DESC LIMIT ?", params + [int(limit)]).fetchall()
            result = []
            for h in headers:
                lines = con.execute("""SELECT l.*,a.name AS account_name FROM journal_lines l
                    JOIN accounting_accounts a ON a.code=l.account_code WHERE l.entry_id=? ORDER BY l.line_no""", (h["id"],)).fetchall()
                result.append({"header": dict(h), "lines": [dict(r) for r in lines]})
            return result

    def trial_balance(self, date_from=None, date_to=None):
        if date_from: date_from = _iso_date(date_from, "از تاریخ")
        if date_to: date_to = _iso_date(date_to, "تا تاریخ")
        if date_from and date_to and date_from > date_to:
            raise ValueError("از تاریخ نباید بعد از تا تاریخ باشد.")
        with self.connect() as con:
            accounts = con.execute("SELECT * FROM accounting_accounts WHERE is_active=1 ORDER BY code").fetchall()
            rows = []
            for a in accounts:
                if date_from:
                    op = con.execute("""SELECT COALESCE(SUM(l.debit_rial),0),COALESCE(SUM(l.credit_rial),0)
                        FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                        WHERE l.account_code=? AND e.entry_date < ? AND e.status='posted'""", (a["code"], date_from)).fetchone()
                else:
                    op = (0, 0)
                clauses, p = ["l.account_code=?", "e.status='posted'"], [a["code"]]
                if date_from: clauses.append("e.entry_date >= ?"); p.append(date_from)
                if date_to: clauses.append("e.entry_date <= ?"); p.append(date_to)
                mov = con.execute("""SELECT COALESCE(SUM(l.debit_rial),0),COALESCE(SUM(l.credit_rial),0)
                    FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id WHERE """ + " AND ".join(clauses), p).fetchone()
                opening_net = int(op[0]) - int(op[1])
                debit, credit = int(mov[0]), int(mov[1])
                closing_net = opening_net + debit - credit
                rows.append({"account_code": a["code"], "account_name": a["name"], "category": a["category"],
                    "opening_debit_rial": max(opening_net, 0), "opening_credit_rial": max(-opening_net, 0),
                    "debit_rial": debit, "credit_rial": credit,
                    "closing_debit_rial": max(closing_net, 0), "closing_credit_rial": max(-closing_net, 0)})
            totals = {key: sum(row[key] for row in rows) for key in
                      ("opening_debit_rial", "opening_credit_rial", "debit_rial", "credit_rial", "closing_debit_rial", "closing_credit_rial")}
            return {"rows": rows, "totals": totals, "is_balanced": totals["closing_debit_rial"] == totals["closing_credit_rial"] and totals["debit_rial"] == totals["credit_rial"]}

    def _account_balances(self, as_of=None, date_from=None):
        if as_of: as_of = _iso_date(as_of, "تا تاریخ")
        if date_from: date_from = _iso_date(date_from, "از تاریخ")
        if as_of and date_from and date_from > as_of:
            raise ValueError("از تاریخ نباید بعد از تا تاریخ باشد.")
        with self.connect() as con:
            accounts = [dict(r) for r in con.execute("SELECT * FROM accounting_accounts WHERE is_active=1 ORDER BY code")]
            for a in accounts:
                clauses, params = ["l.account_code=?", "e.status='posted'"], [a["code"]]
                if date_from: clauses.append("e.entry_date >= ?"); params.append(date_from)
                if as_of: clauses.append("e.entry_date <= ?"); params.append(as_of)
                row = con.execute("""SELECT COALESCE(SUM(l.debit_rial),0),COALESCE(SUM(l.credit_rial),0)
                    FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id WHERE """ + " AND ".join(clauses), params).fetchone()
                a["debit_rial"] = int(row[0]); a["credit_rial"] = int(row[1])
                a["raw_net_rial"] = a["debit_rial"] - a["credit_rial"]
                a["natural_balance_rial"] = a["raw_net_rial"] if a["normal_side"] == "debit" else -a["raw_net_rial"]
            return accounts

    def income_statement(self, date_from, date_to):
        date_from, date_to = _iso_date(date_from, "از تاریخ"), _iso_date(date_to, "تا تاریخ")
        if date_from > date_to: raise ValueError("از تاریخ نباید بعد از تا تاریخ باشد.")
        balances = self._account_balances(as_of=date_to, date_from=date_from)
        revenues = [a for a in balances if a["category"] == "revenue"]
        expenses = [a for a in balances if a["category"] == "expense"]
        revenue_total = sum(a["natural_balance_rial"] for a in revenues)
        expense_total = sum(a["natural_balance_rial"] for a in expenses)
        return {"date_from": date_from, "date_to": date_to, "revenues": revenues, "expenses": expenses,
                "revenue_total_rial": revenue_total, "expense_total_rial": expense_total,
                "net_profit_rial": revenue_total - expense_total}

    def balance_sheet(self, as_of):
        as_of = _iso_date(as_of, "ترازنامه تا تاریخ")
        balances = self._account_balances(as_of=as_of)
        assets = [a for a in balances if a["category"] == "asset"]
        liabilities = [a for a in balances if a["category"] == "liability"]
        equity = [a for a in balances if a["category"] == "equity"]
        revenues = [a for a in balances if a["category"] == "revenue"]
        expenses = [a for a in balances if a["category"] == "expense"]
        # Assets are shown as debit minus credit; liabilities and equity as credit minus debit.
        assets_total = sum(a["raw_net_rial"] for a in assets)
        liabilities_total = sum(-a["raw_net_rial"] for a in liabilities)
        equity_account_total = sum(-a["raw_net_rial"] for a in equity)
        current_earnings = sum(-a["raw_net_rial"] for a in revenues) - sum(a["raw_net_rial"] for a in expenses)
        equity_total = equity_account_total + current_earnings
        return {"as_of": as_of, "assets": assets, "liabilities": liabilities, "equity": equity,
                "current_earnings_rial": current_earnings, "assets_total_rial": assets_total,
                "liabilities_total_rial": liabilities_total, "equity_accounts_total_rial": equity_account_total,
                "equity_total_rial": equity_total, "liabilities_equity_total_rial": liabilities_total + equity_total,
                "difference_rial": assets_total - liabilities_total - equity_total,
                "is_balanced": assets_total == liabilities_total + equity_total}

    def cash_flow_statement(self, date_from, date_to):
        """Direct cash movement report, classified by counterpart account mapping.

        Each journal's net cash movement is apportioned across the cash_flow_class
        of its non-cash counterpart lines by their absolute value. This is useful
        managerial output; a qualified accountant should approve mappings and edge
        cases before statutory reliance.
        """
        date_from, date_to = _iso_date(date_from, "از تاریخ"), _iso_date(date_to, "تا تاریخ")
        if date_from > date_to: raise ValueError("از تاریخ نباید بعد از تا تاریخ باشد.")
        classes = {k: 0 for k in ("operating", "investing", "financing", "other")}
        with self.connect() as con:
            entries = con.execute("SELECT * FROM journal_entries WHERE status='posted' AND entry_date>=? AND entry_date<=? ORDER BY entry_date,id", (date_from, date_to)).fetchall()
            cash_codes = {r[0] for r in con.execute("SELECT code FROM accounting_accounts WHERE is_active=1 AND is_cash=1").fetchall()}
            account_classes = {r[0]: r[1] for r in con.execute("SELECT code,cash_flow_class FROM accounting_accounts WHERE is_active=1").fetchall()}
            for entry in entries:
                lines = [dict(r) for r in con.execute("SELECT * FROM journal_lines WHERE entry_id=?", (entry["id"],)).fetchall()]
                cash_delta = sum((l["debit_rial"] - l["credit_rial"]) for l in lines if l["account_code"] in cash_codes)
                if cash_delta == 0:
                    continue
                weights = {}
                for line in lines:
                    if line["account_code"] not in cash_codes:
                        category = account_classes.get(line["account_code"], "operating")
                        weights[category] = weights.get(category, 0) + line["debit_rial"] + line["credit_rial"]
                if not weights:
                    weights["other"] = 1
                total_weight = sum(weights.values())
                remaining = cash_delta
                ordered = sorted(weights.items())
                for index, (category, weight) in enumerate(ordered):
                    portion = remaining if index == len(ordered) - 1 else int(Decimal(cash_delta * weight) / Decimal(total_weight))
                    classes[category] += portion
                    remaining -= portion
        opening = self._cash_total_before(date_from)
        closing = self._cash_total_through(date_to)
        net_change = sum(classes.values())
        return {"date_from": date_from, "date_to": date_to, "operating_rial": classes["operating"],
                "investing_rial": classes["investing"], "financing_rial": classes["financing"],
                "other_rial": classes["other"], "net_change_rial": net_change,
                "opening_cash_rial": opening, "closing_cash_rial": closing,
                "reconciles": opening + net_change == closing}

    def _cash_total_before(self, date_before):
        with self.connect() as con:
            row = con.execute("""SELECT COALESCE(SUM(l.debit_rial-l.credit_rial),0)
                FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                JOIN accounting_accounts a ON a.code=l.account_code
                WHERE a.is_cash=1 AND a.is_active=1 AND e.entry_date < ? AND e.status='posted'""", (_iso_date(date_before),)).fetchone()
            return int(row[0])

    def _cash_total_through(self, date_to):
        with self.connect() as con:
            row = con.execute("""SELECT COALESCE(SUM(l.debit_rial-l.credit_rial),0)
                FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                JOIN accounting_accounts a ON a.code=l.account_code
                WHERE a.is_cash=1 AND a.is_active=1 AND e.entry_date <= ? AND e.status='posted'""", (_iso_date(date_to),)).fetchone()
            return int(row[0])

    def financial_ratios(self, as_of, period_from, period_to):
        bs = self.balance_sheet(as_of)
        income = self.income_statement(period_from, period_to)
        assets_total = bs["assets_total_rial"]
        liab_total = bs["liabilities_total_rial"]
        current_assets = sum(a["raw_net_rial"] for a in bs["assets"] if a["code"].startswith(("10", "11", "12", "13")))
        # The mapping is intentionally heuristic until the user/accountant defines current/non-current flags.
        current_liabilities = sum(-a["raw_net_rial"] for a in bs["liabilities"] if a["code"].startswith(("20", "22")))
        return {"as_of": bs["as_of"], "current_assets_rial": current_assets,
                "current_liabilities_rial": current_liabilities,
                "current_ratio": (Decimal(current_assets) / Decimal(current_liabilities)) if current_liabilities else None,
                "liabilities_to_assets": (Decimal(liab_total) / Decimal(assets_total)) if assets_total else None,
                "net_profit_margin": (Decimal(income["net_profit_rial"]) / Decimal(income["revenue_total_rial"])) if income["revenue_total_rial"] else None,
                "net_profit_rial": income["net_profit_rial"], "assets_total_rial": assets_total,
                "liabilities_total_rial": liab_total,
                "note": "نسبت جاری بر اساس پیشوند کد حساب تخمین زده می‌شود؛ برای گزارش مدیریتی قطعی، پرچم جاری/غیرجاری باید روی سرفصل‌ها تنظیم شود."}

    def account_ledger(self, account_code, date_from=None, date_to=None):
        clauses, params = ["l.account_code=?", "e.status='posted'"], [str(account_code)]
        if date_from: clauses.append("e.entry_date >= ?"); params.append(_iso_date(date_from, "از تاریخ"))
        if date_to: clauses.append("e.entry_date <= ?"); params.append(_iso_date(date_to, "تا تاریخ"))
        with self.connect() as con:
            a = con.execute("SELECT * FROM accounting_accounts WHERE code=?", (str(account_code),)).fetchone()
            if not a: raise ValueError("کد حساب وجود ندارد.")
            lines = con.execute("""SELECT e.entry_no,e.entry_date,e.description AS entry_description,
                    l.line_no,l.description,l.debit_rial,l.credit_rial,l.party_ref,l.cost_center
                FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id WHERE """ + " AND ".join(clauses) + " ORDER BY e.entry_date,e.id,l.line_no", params).fetchall()
            return {"account": dict(a), "lines": [dict(r) for r in lines]}
