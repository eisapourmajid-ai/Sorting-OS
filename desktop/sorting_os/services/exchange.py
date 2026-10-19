# -*- coding: utf-8 -*-
"""Universal import/export engine (Prompt 21).

Every import follows the same four steps:

1. **preview** - rows are parsed and validated, nothing is written yet;
2. **mapping** - the operator maps source columns to target fields, and the
   money unit is chosen explicitly (never guessed from the numbers);
3. **commit** - only valid rows are written, each row keeps its own status and
   error message;
4. **idempotency** - the batch is identified by a key (usually the file
   checksum).  Importing the same file twice never duplicates data.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso, to_rial

#: Entities that can be imported/exported and their target fields.
ENTITIES = {
    "parties": {
        "label": "اشخاص",
        "fields": ("display_name", "phone", "national_id", "address", "legal_name", "notes"),
        "required": ("display_name",),
    },
    "shipments": {
        "label": "محموله‌ها",
        "fields": ("owner_party_id", "product_name", "received_weight", "received_at",
                   "ownership_model", "contract_ref", "notes"),
        "required": ("owner_party_id", "product_name", "received_weight"),
    },
    "invoices": {
        "label": "فاکتورها",
        "fields": ("party_id", "invoice_type", "document_date", "amount", "kind", "doc_number",
                   "description"),
        "required": ("party_id", "document_date", "amount"),
    },
    "payments": {
        "label": "دریافت/پرداخت‌ها",
        "fields": ("party_id", "direction", "amount", "payment_date", "method", "note"),
        "required": ("party_id", "direction", "amount", "payment_date"),
    },
    "bank_transactions": {
        "label": "گردش بانکی",
        "fields": ("transaction_date", "description", "amount", "direction", "reference"),
        "required": ("transaction_date", "amount", "direction"),
    },
    "products": {
        "label": "محصولات",
        "fields": ("code", "name", "category", "base_unit", "notes"),
        "required": ("code", "name"),
    },
}

#: Columns that hold money.  They are converted with the operator's unit.
MONEY_FIELDS = ("amount", "received_weight")
#: Columns that hold dates.
DATE_FIELDS = ("received_at", "document_date", "payment_date", "transaction_date")


def file_checksum(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_csv_rows(source):
    """Read CSV rows from a path, a file-like object or a list of dicts."""
    if isinstance(source, list):
        return [dict(row) for row in source]
    if hasattr(source, "read"):
        text = source.read()
        if isinstance(text, bytes):
            text = text.decode("utf-8-sig")
        return [dict(row) for row in csv.DictReader(io.StringIO(text))]
    path = str(source)
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


#: Common Persian/English headers understood without an explicit mapping.
HEADER_ALIASES = {
    "display_name": ("نام", "نام شخص", "نام و نام خانوادگی", "name", "display_name"),
    "phone": ("تلفن", "موبایل", "شماره تماس", "phone", "mobile"),
    "national_id": ("کد ملی", "کدملی", "شماره ملی", "national_id", "national code"),
    "address": ("آدرس", "نشانی", "address"),
    "legal_name": ("نام حقوقی", "legal_name"),
    "notes": ("یادداشت", "توضیحات", "notes"),
    "code": ("کد", "code"),
    "name": ("نام", "name"),
    "category": ("دسته", "گروه", "category"),
    "base_unit": ("واحد", "unit", "base_unit"),
    "party_id": ("کد طرف", "طرف حساب", "party_id"),
    "document_date": ("تاریخ سند", "تاریخ فاکتور", "document_date", "date"),
    "amount": ("مبلغ", "مبلغ کل", "amount", "مبلغ (ریال)"),
    "kind": ("نوع سند", "kind"),
    "invoice_type": ("نوع فاکتور", "invoice_type"),
    "doc_number": ("شماره سند", "شماره فاکتور", "doc_number"),
    "description": ("شرح", "توضیح", "description"),
    "direction": ("جهت", "نوع", "direction"),
    "payment_date": ("تاریخ پرداخت", "تاریخ دریافت", "payment_date"),
    "method": ("روش", "method"),
    "transaction_date": ("تاریخ تراکنش", "تاریخ", "transaction_date"),
    "reference": ("شماره مرجع", "reference", "پیگیری"),
    "owner_party_id": ("کد مالک", "مالک", "owner_party_id"),
    "product_name": ("نام محصول", "محصول", "product_name"),
    "received_weight": ("وزن", "وزن دریافتی", "received_weight"),
    "received_at": ("تاریخ دریافت", "received_at"),
    "ownership_model": ("مدل مالکیت", "ownership_model"),
    "contract_ref": ("شماره قرارداد", "contract_ref"),
}


class ExchangeService:
    """Preview/commit imports and audited exports."""

    def __init__(self, db):
        self.db = db

    # -- import ------------------------------------------------------------- #
    def preview(self, entity, rows, mapping=None, unit="ریال", file_name=None,
                actor="کاربر محلی", batch_key=None):
        """Validate a file and return a preview batch (nothing is written)."""
        if entity not in ENTITIES:
            raise ValidationError("نوع داده پشتیبانی نمی‌شود: %s" % entity)
        spec = ENTITIES[entity]
        rows = rows or []
        if not rows:
            raise ValidationError("فایل ورودی خالی است.")
        if unit not in ("ریال", "تومان"):
            raise ValidationError("واحد مبلغ باید صریحاً «ریال» یا «تومان» باشد.")
        mapping = dict(mapping or {})
        aliases = self._resolve_aliases(rows[0].keys(), mapping, spec)
        checksum = file_checksum(json.dumps(rows, ensure_ascii=False, sort_keys=True))
        key = batch_key or "%s:%s:%s" % (entity, unit, checksum)
        with self.db.reader() as con:
            existing = con.execute(
                "SELECT id, status, row_count FROM import_batches WHERE batch_key=?", (key,)).fetchone()
        if existing and existing["status"] == "committed":
            return {"batch_id": existing["id"], "duplicate": True, "status": "committed",
                    "rows": [], "errors": [], "row_count": existing["row_count"]}
        prepared, errors = [], []
        for index, row in enumerate(rows, 1):
            target = {}
            for field in spec["fields"]:
                source_column = mapping.get(field) or aliases.get(field)
                if source_column and source_column in row:
                    target[field] = row[source_column]
                elif field in row:
                    target[field] = row[field]
            try:
                for field in spec["required"]:
                    if target.get(field) in (None, ""):
                        raise ValidationError("فیلد «%s» الزامی است." % field)
                if "amount" in target:
                    target["amount"] = to_rial(target["amount"], unit, "مبلغ")
                if "received_weight" in target and entity == "shipments":
                    target["received_weight"] = float(target["received_weight"])
                for field in DATE_FIELDS:
                    if target.get(field):
                        target[field] = normalize_iso_date(target[field], field)
                prepared.append({"row_no": index, "target": target})
            except (ValidationError, ValueError) as exc:
                errors.append({"row_no": index, "error": str(exc), "raw": row})
        stamp = now_iso()
        with self.db.transaction() as con:
            cur = con.execute(
                """INSERT INTO import_batches(batch_key, entity, file_name, unit, mapping_json,
                        status, row_count, error_count, created_at, created_by)
                   VALUES(?,?,?,?,?, 'preview', ?,?,?,?)""",
                (key, entity, str(file_name or "").strip() or None, unit,
                 json.dumps(mapping, ensure_ascii=False), len(prepared), len(errors), stamp, actor))
            batch_id = cur.lastrowid
            for item in prepared:
                con.execute(
                    """INSERT INTO import_batch_rows(batch_id, row_no, action, status, payload_json,
                            created_at)
                       VALUES(?,?,?, 'ready', ?, ?)""",
                    (batch_id, item["row_no"], "insert",
                     json.dumps(item["target"], ensure_ascii=False), stamp))
            for item in errors:
                con.execute(
                    """INSERT INTO import_batch_rows(batch_id, row_no, action, status, error,
                            payload_json, created_at)
                       VALUES(?,?,?, 'error', ?, ?, ?)""",
                    (batch_id, item["row_no"], "reject", item["error"],
                     json.dumps(item["raw"], ensure_ascii=False, default=str), stamp))
            self.db.audit(actor, "import_preview", "import_batch", batch_id,
                          "%s; %d ready / %d error" % (entity, len(prepared), len(errors)), con)
        return {"batch_id": batch_id, "duplicate": False, "status": "preview",
                "rows": prepared, "errors": errors, "row_count": len(prepared),
                "error_count": len(errors), "batch_key": key}

    @staticmethod
    def _resolve_aliases(headers, mapping, spec):
        """Match known Persian/English headers to target fields."""
        aliases = {}
        headers = list(headers or [])
        for field in spec["fields"]:
            if field in mapping:
                continue
            for candidate in HEADER_ALIASES.get(field, ()):  # explicit alias first
                if candidate in headers:
                    aliases[field] = candidate
                    break
        return aliases

    def commit(self, batch_id, actor="کاربر محلی"):
        """Write the previewed rows.  Rejected rows are skipped, not fatal."""
        with self.db.reader() as con:
            batch = con.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,)).fetchone()
            if not batch:
                raise ValidationError("batch یافت نشد.")
            if batch["status"] == "committed":
                return {"batch_id": batch_id, "committed": 0, "duplicate": True}
            rows = con.execute(
                "SELECT * FROM import_batch_rows WHERE batch_id=? AND status='ready' ORDER BY row_no",
                (batch_id,)).fetchall()
        entity = batch["entity"]
        committed = 0
        failures = []
        for row in rows:
            target = json.loads(row["payload_json"])
            try:
                self._write(entity, target, actor)
                committed += 1
                with self.db.transaction() as con:
                    con.execute("UPDATE import_batch_rows SET status='committed', action='insert'"
                                " WHERE id=?", (row["id"],))
            except (ValidationError, ConflictError, ValueError) as exc:
                failures.append({"row_no": row["row_no"], "error": str(exc)})
                with self.db.transaction() as con:
                    con.execute("UPDATE import_batch_rows SET status='failed', error=?"
                                " WHERE id=?", (str(exc), row["id"]))
        with self.db.transaction() as con:
            con.execute(
                "UPDATE import_batches SET status='committed', row_count=?, committed_at=?"
                " WHERE id=?",
                (committed, now_iso(), batch_id))
            self.db.audit(actor, "import_commit", "import_batch", batch_id,
                          "%d committed / %d failed" % (committed, len(failures)), con)
        return {"batch_id": batch_id, "committed": committed, "failed": failures,
                "duplicate": False}

    def _write(self, entity, target, actor):
        """Write a single previewed row through the domain services."""
        if entity == "parties":
            from .parties import PartyService

            return PartyService(self.db).create(
                display_name=target.get("display_name"),
                phone=target.get("phone"),
                national_id=target.get("national_id"),
                address=target.get("address"),
                roles=["owner"],
                legal_name=target.get("legal_name"),
                notes=target.get("notes"),
                actor=actor)
        if entity == "products":
            from .catalog import CatalogService

            return CatalogService(self.db).create_product(
                code=target.get("code"), name=target.get("name"),
                category=target.get("category"), base_unit=target.get("base_unit") or "کیلوگرم",
                notes=target.get("notes"), actor=actor)
        if entity == "shipments":
            from .operations import OperationsService

            return OperationsService(self.db).create_shipment(
                owner_party_id=int(target["owner_party_id"]),
                product_name=target.get("product_name"),
                weight_kg=target.get("received_weight", 0),
                received_at=target.get("received_at"),
                ownership_model=target.get("ownership_model") or "undetermined",
                contract_ref=target.get("contract_ref"),
                notes=target.get("notes"), actor=actor)
        if entity == "invoices":
            from .documents import DocumentService

            service = DocumentService(self.db)
            amount = to_rial(target["amount"], "ریال", "مبلغ")
            return service.create_invoice(
                party_id=int(target["party_id"]),
                kind=target.get("kind") or "sales",
                document_date=target.get("document_date"),
                lines=[{"description": target.get("description") or "ردیف واردشده",
                        "quantity": 1, "unit": "عدد", "unit_price": amount, "weight_kg": 0,
                        "billing_weight_kg": 1}],
                invoice_type=target.get("invoice_type") or "فروش",
                description=target.get("description") or "",
                doc_number=target.get("doc_number"), status="draft", actor=actor)
        if entity == "payments":
            from .banking import BankingService

            return BankingService(self.db).create_payment(
                party_id=int(target["party_id"]), direction=target.get("direction"),
                amount_rial=target["amount"], payment_date=target.get("payment_date"),
                method=target.get("method") or "bank", note=target.get("note") or "", actor=actor)
        if entity == "bank_transactions":
            from .banking import BankingService

            service = BankingService(self.db)
            preview = service.import_statement(
                self.db.get_setting("default_bank_account_id", 1) or 1,
                [{"date": target["transaction_date"], "description": target.get("description"),
                  "amount": target["amount"], "direction": target.get("direction"),
                  "reference": target.get("reference")}],
                unit="ریال", file_name="import", actor=actor)
            return preview["statement_id"]
        raise ValidationError("نوع داده پشتیبانی نمی‌شود: %s" % entity)

    # -- export ------------------------------------------------------------- #
    def export(self, entity, target_path=None, unit="ریال", actor="کاربر محلی"):
        """Export data as CSV with a canonical rial column and a display column."""
        if entity not in ENTITIES:
            raise ValidationError("نوع داده پشتیبانی نمی‌شود: %s" % entity)
        rows = self._export_rows(entity)
        if not rows:
            rows = []
        header = list(ENTITIES[entity]["fields"])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for row in rows:
            writer.writerow(["" if row.get(field) is None else row.get(field) for field in header])
        text = output.getvalue()
        checksum = file_checksum(text)
        if target_path:
            with open(target_path, "w", encoding="utf-8-sig", newline="") as handle:
                handle.write(text)
        with self.db.transaction() as con:
            cur = con.execute(
                """INSERT INTO export_batches(entity, file_name, row_count, checksum, created_at,
                        created_by)
                   VALUES(?,?,?,?,?,?)""",
                (entity, os.path.basename(target_path) if target_path else None, len(rows),
                 checksum, now_iso(), actor))
            self.db.audit(actor, "export", "export_batch", cur.lastrowid,
                          "%s; %d rows" % (entity, len(rows)), con)
        return {"entity": entity, "row_count": len(rows), "sha256": checksum,
                "path": target_path, "csv": text}

    def _export_rows(self, entity):
        with self.db.reader() as con:
            if entity == "parties":
                rows = con.execute(
                    """SELECT display_name, phone, national_id, address, legal_name, notes
                       FROM parties WHERE is_active=1 ORDER BY id""").fetchall()
                return [dict(r) for r in rows]
            if entity == "products":
                rows = con.execute(
                    "SELECT code, name, category, base_unit, notes FROM products"
                    " WHERE is_active=1 ORDER BY id").fetchall()
                return [dict(r) for r in rows]
            if entity == "shipments":
                rows = con.execute(
                    """SELECT s.owner_party_id, s.product_name, s.received_weight, s.received_at,
                              s.ownership_model, s.contract_ref, s.notes
                       FROM shipments s ORDER BY s.id""").fetchall()
                return [dict(r) for r in rows]
            if entity == "invoices":
                rows = con.execute(
                    """SELECT i.party_id, i.invoice_type, i.document_date, i.amount_rial AS amount,
                              i.kind, i.doc_number, i.description
                       FROM invoices i WHERE i.amount_rial IS NOT NULL ORDER BY i.id""").fetchall()
                return [dict(r) for r in rows]
            if entity == "payments":
                rows = con.execute(
                    """SELECT party_id, direction, amount_rial AS amount, payment_date, method, note
                       FROM payments ORDER BY id""").fetchall()
                return [dict(r) for r in rows]
            if entity == "bank_transactions":
                rows = con.execute(
                    """SELECT transaction_date, description, amount_rial AS amount, direction,
                              reference FROM bank_transactions ORDER BY id""").fetchall()
                return [dict(r) for r in rows]
        return []

    def list_batches(self, limit=50):
        with self.db.reader() as con:
            rows = con.execute(
                "SELECT * FROM import_batches ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]
