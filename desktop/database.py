# -*- coding: utf-8 -*-
"""Local SQLite persistence for SORTING OS desktop foundation.
Compatible with Python 3.8+; standard-library only.
"""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

SCHEMA_VERSION = 1


class _ClosingConnection(sqlite3.Connection):
    """Commit/rollback via sqlite context semantics and close deterministically."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

SCHEMA = r"""
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    display_name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    roles TEXT NOT NULL DEFAULT 'مالک کالا',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_parties_name ON parties(display_name);
CREATE INDEX IF NOT EXISTS ix_parties_national_id ON parties(national_id);
CREATE INDEX IF NOT EXISTS ix_parties_phone ON parties(phone);
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    owner_party_id INTEGER NOT NULL REFERENCES parties(id),
    product_name TEXT NOT NULL,
    received_weight REAL NOT NULL CHECK(received_weight >= 0),
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'دریافت‌شده',
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_shipments_owner ON shipments(owner_party_id);
CREATE INDEX IF NOT EXISTS ix_shipments_received_at ON shipments(received_at);
CREATE TABLE IF NOT EXISTS weighing_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    ticket_type TEXT NOT NULL,
    shipment_id INTEGER REFERENCES shipments(id),
    vehicle_plate TEXT,
    driver_name TEXT,
    gross_weight REAL NOT NULL CHECK(gross_weight >= 0),
    tare_weight REAL NOT NULL CHECK(tare_weight >= 0),
    net_weight REAL NOT NULL CHECK(net_weight >= 0),
    weighed_at TEXT NOT NULL,
    operator_name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    CHECK(gross_weight >= tare_weight)
);
CREATE INDEX IF NOT EXISTS ix_weighings_shipment ON weighing_tickets(shipment_id);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    invoice_type TEXT NOT NULL,
    document_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    description TEXT,
    shipment_id INTEGER REFERENCES shipments(id),
    status TEXT NOT NULL DEFAULT 'پیش‌نویس',
    created_at TEXT NOT NULL,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS ix_invoices_party ON invoices(party_id);
CREATE INDEX IF NOT EXISTS ix_invoices_date ON invoices(document_date);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT
);
"""


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


class Database:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        parent = os.path.dirname(self.path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        self._initialize()

    def connect(self):
        con = sqlite3.connect(self.path, timeout=20, factory=_ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 20000")
        return con

    @contextmanager
    def transaction(self):
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _initialize(self):
        with self.connect() as con:
            con.executescript(SCHEMA)
            con.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))

    def audit(self, actor, action, entity_type, entity_id=None, details=None, con=None):
        own = con is None
        if own:
            con = self.connect()
        try:
            con.execute(
                "INSERT INTO audit_log(event_at,actor,action,entity_type,entity_id,details) VALUES(?,?,?,?,?,?)",
                (now_iso(), actor or "کاربر محلی", action, entity_type, None if entity_id is None else str(entity_id), details or ""),
            )
            if own:
                con.commit()
        finally:
            if own:
                con.close()

    def counts(self):
        with self.connect() as con:
            return {
                "parties": con.execute("SELECT COUNT(*) FROM parties WHERE is_active=1").fetchone()[0],
                "shipments": con.execute("SELECT COUNT(*) FROM shipments WHERE status <> 'بسته‌شده'").fetchone()[0],
                "weighings": con.execute("SELECT COUNT(*) FROM weighing_tickets").fetchone()[0],
                "invoices": con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0],
                "invoice_amount": con.execute("SELECT COALESCE(SUM(amount),0) FROM invoices WHERE status='قطعی'").fetchone()[0],
                "received_weight": con.execute("SELECT COALESCE(SUM(received_weight),0) FROM shipments").fetchone()[0],
            }

    def list_parties(self, search="", active_only=False):
        sql = "SELECT * FROM parties WHERE 1=1"
        params = []
        if active_only:
            sql += " AND is_active=1"
        if search.strip():
            q = "%" + search.strip() + "%"
            sql += " AND (display_name LIKE ? OR phone LIKE ? OR national_id LIKE ? OR code LIKE ?)"
            params.extend([q, q, q, q])
        sql += " ORDER BY display_name COLLATE NOCASE"
        with self.connect() as con:
            return con.execute(sql, params).fetchall()

    def save_party(self, values, party_id=None, actor="کاربر محلی"):
        name = values.get("display_name", "").strip()
        if not name:
            raise ValueError("نام شخص الزامی است.")
        stamp = now_iso()
        with self.transaction() as con:
            national_id = (values.get("national_id") or "").strip() or None
            phone = (values.get("phone") or "").strip() or None
            if national_id:
                hit = con.execute("SELECT id,display_name FROM parties WHERE national_id=? AND id<>COALESCE(?, -1)", (national_id, party_id)).fetchone()
                if hit:
                    raise ValueError("این کد ملی قبلاً برای «%s» ثبت شده است. ادغام خودکار انجام نشد." % hit["display_name"])
            if party_id:
                con.execute("""UPDATE parties SET display_name=?,phone=?,national_id=?,address=?,roles=?,updated_at=? WHERE id=?""",
                    (name, phone, national_id, values.get("address", "").strip(), values.get("roles", "مالک کالا").strip() or "سایر", stamp, party_id))
                entity_id, action = party_id, "update"
            else:
                code = "PTY-%s" % (stamp.replace("-", "").replace(":", "").replace(" ", "").replace("T", "") + "-%03d" % (int(datetime.now().microsecond / 1000)))
                cur = con.execute("""INSERT INTO parties(code,display_name,phone,national_id,address,roles,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?)""", (code, name, phone, national_id, values.get("address", "").strip(), values.get("roles", "مالک کالا").strip() or "سایر", stamp, stamp))
                entity_id, action = cur.lastrowid, "create"
            self.audit(actor, action, "party", entity_id, name, con)
            return entity_id

    def create_shipment(self, owner_id, product_name, weight, received_at=None, notes="", actor="کاربر محلی"):
        product_name = product_name.strip()
        if not product_name:
            raise ValueError("نام محصول الزامی است.")
        weight = float(weight)
        if weight < 0:
            raise ValueError("وزن نمی‌تواند منفی باشد.")
        stamp = now_iso()
        received_at = received_at or stamp
        with self.transaction() as con:
            if not con.execute("SELECT 1 FROM parties WHERE id=? AND is_active=1", (owner_id,)).fetchone():
                raise ValueError("مالک انتخاب‌شده معتبر یا فعال نیست.")
            code = "SHP-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            cur = con.execute("INSERT INTO shipments(code,owner_party_id,product_name,received_weight,received_at,notes,created_at) VALUES(?,?,?,?,?,?,?)",
                (code, owner_id, product_name, weight, received_at, notes.strip(), stamp))
            self.audit(actor, "create", "shipment", cur.lastrowid, code, con)
            return cur.lastrowid

    def create_weighing(self, ticket_type, gross, tare, shipment_id=None, plate="", driver="", weighed_at=None, operator="", notes="", actor="کاربر محلی"):
        gross, tare = float(gross), float(tare)
        if gross < 0 or tare < 0:
            raise ValueError("وزن‌ها نمی‌توانند منفی باشند.")
        if gross < tare:
            raise ValueError("وزن ناخالص نمی‌تواند کمتر از وزن خالی باشد.")
        net = round(gross - tare, 3)
        stamp = now_iso()
        weighed_at = weighed_at or stamp
        with self.transaction() as con:
            if shipment_id is not None and not con.execute("SELECT 1 FROM shipments WHERE id=?", (shipment_id,)).fetchone():
                raise ValueError("محموله انتخاب‌شده وجود ندارد.")
            code = "WGH-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            cur = con.execute("""INSERT INTO weighing_tickets(code,ticket_type,shipment_id,vehicle_plate,driver_name,gross_weight,tare_weight,net_weight,weighed_at,operator_name,notes,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (code, ticket_type, shipment_id, plate.strip(), driver.strip(), gross, tare, net, weighed_at, operator.strip(), notes.strip(), stamp))
            self.audit(actor, "create", "weighing_ticket", cur.lastrowid, "%s; net=%s" % (code, net), con)
            return cur.lastrowid

    def create_invoice(self, party_id, invoice_type, document_date, amount, description="", shipment_id=None, status="پیش‌نویس", actor="کاربر محلی"):
        amount = float(amount)
        if amount < 0:
            raise ValueError("مبلغ نمی‌تواند منفی باشد.")
        if status not in ("پیش‌نویس", "قطعی", "لغوشده"):
            raise ValueError("وضعیت سند نامعتبر است.")
        stamp = now_iso()
        with self.transaction() as con:
            if not con.execute("SELECT 1 FROM parties WHERE id=?", (party_id,)).fetchone():
                raise ValueError("طرف حساب وجود ندارد.")
            code = "INV-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            cur = con.execute("""INSERT INTO invoices(code,party_id,invoice_type,document_date,amount,description,shipment_id,status,created_at,created_by)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (code, party_id, invoice_type, document_date, amount, description.strip(), shipment_id, status, stamp, actor))
            self.audit(actor, "create", "invoice", cur.lastrowid, "%s; %s; %s" % (code, status, amount), con)
            return cur.lastrowid

    def export_rows(self, entity):
        allowed = {"parties": "SELECT code,display_name,phone,national_id,address,roles,is_active,created_at FROM parties ORDER BY id",
                   "shipments": "SELECT s.code,p.display_name AS owner, s.product_name,s.received_weight,s.received_at,s.status,s.notes FROM shipments s JOIN parties p ON p.id=s.owner_party_id ORDER BY s.id",
                   "weighings": "SELECT code,ticket_type,shipment_id,vehicle_plate,driver_name,gross_weight,tare_weight,net_weight,weighed_at,operator_name,notes FROM weighing_tickets ORDER BY id",
                   "invoices": "SELECT i.code,p.display_name AS party,i.invoice_type,i.document_date,i.amount,i.description,s.code AS shipment,i.status FROM invoices i JOIN parties p ON p.id=i.party_id LEFT JOIN shipments s ON s.id=i.shipment_id ORDER BY i.id"}
        if entity not in allowed:
            raise ValueError("نوع خروجی پشتیبانی نمی‌شود.")
        with self.connect() as con:
            cur = con.execute(allowed[entity])
            return [ [d[0] for d in cur.description] ] + [list(row) for row in cur.fetchall()]

    def import_parties_preview(self, rows):
        """Returns actions; never auto-merges solely by name."""
        result = []
        with self.connect() as con:
            existing = con.execute("SELECT id,display_name,phone,national_id FROM parties").fetchall()
        for index, row in enumerate(rows, 1):
            name = (row.get("display_name") or row.get("نام") or row.get("name") or "").strip()
            phone = (row.get("phone") or row.get("تلفن") or row.get("موبایل") or "").strip()
            nid = (row.get("national_id") or row.get("کد ملی") or row.get("کدملی") or "").strip()
            if not name:
                action, reason = "skip", "نام خالی است"
            elif nid and any((p["national_id"] or "").strip() == nid for p in existing):
                action, reason = "review", "کد ملی موجود است؛ تطبیق/به‌روزرسانی دستی لازم است"
            elif phone and any((p["phone"] or "").strip() == phone and (p["display_name"] or "").strip().casefold() == name.casefold() for p in existing):
                action, reason = "review", "نام و تلفن مشابه؛ ادغام خودکار ممنوع"
            elif any((p["display_name"] or "").strip().casefold() == name.casefold() for p in existing):
                action, reason = "review", "نام مشابه؛ مدرک هویتی کافی نیست"
            else:
                action, reason = "insert", "شخص جدید؛ قابل افزودن پس از تأیید"
            result.append({"row": index, "display_name": name, "phone": phone, "national_id": nid, "action": action, "reason": reason, "source": row})
        return result

    def import_new_party(self, item, actor="درون‌ریزی CSV"):
        if item.get("action") != "insert":
            raise ValueError("فقط ردیف‌های بدون تعارض قابل افزودن مستقیم هستند.")
        return self.save_party({"display_name": item["display_name"], "phone": item["phone"], "national_id": item["national_id"],
                                "address": item["source"].get("address", ""), "roles": item["source"].get("roles", "مالک کالا")}, actor=actor)

    def list_shipments(self):
        with self.connect() as con:
            return con.execute("""SELECT s.*,p.display_name AS owner_name FROM shipments s JOIN parties p ON p.id=s.owner_party_id ORDER BY s.id DESC""").fetchall()

    def list_weighings(self):
        with self.connect() as con:
            return con.execute("""SELECT w.*,s.code AS shipment_code FROM weighing_tickets w LEFT JOIN shipments s ON s.id=w.shipment_id ORDER BY w.id DESC""").fetchall()

    def list_invoices(self):
        with self.connect() as con:
            return con.execute("""SELECT i.*,p.display_name AS party_name,s.code AS shipment_code FROM invoices i JOIN parties p ON p.id=i.party_id LEFT JOIN shipments s ON s.id=i.shipment_id ORDER BY i.id DESC""").fetchall()

    def list_audit(self, limit=100):
        with self.connect() as con:
            return con.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
