# -*- coding: utf-8 -*-
"""Versioned, local print templates with an offline preview (Prompt 23).

Templates live in the database, are versioned and never reach out to the
network.  A template is a small JSON document:

    {
      "title": "صورتحساب",
      "header": ["مؤسسه ...", "شماره سند: {code}"],
      "fields": ["document_date", "party_name", "total_display"],
      "footer": "واحد مبالغ: {unit}"
    }

The renderer substitutes ``{field}`` placeholders from the payload and always
prints the money unit - a number without a unit is not allowed (Prompt 24).
"""
from __future__ import annotations

import json

from ..core import ConflictError, ValidationError, format_money, now_iso

#: Built-in starter templates (also usable without the database).
DEFAULT_TEMPLATES = {
    "weighing_ticket": {
        "title": "باسکول توزین",
        "header": ["SORTING OS", "شماره: {code}", "تاریخ: {weighed_at}"],
        "fields": ["vehicle_plate", "driver_name", "gross_weight", "tare_weight", "net_weight"],
        "footer": "اپراتور: {operator}",
    },
    "invoice": {
        "title": "صورتحساب",
        "header": ["SORTING OS", "شماره سند: {code}", "تاریخ: {document_date}"],
        "fields": ["party_name", "total_display"],
        "footer": "واحد مبالغ: {unit}",
    },
    "settlement": {
        "title": "صورتحساب صافی",
        "header": ["SORTING OS", "شماره صافی: {code}"],
        "fields": ["party_name", "net_display", "commission_display"],
        "footer": "واحد مبالغ: {unit}",
    },
    "dispatch": {
        "title": "حواله خروج",
        "header": ["SORTING OS", "شماره حواله: {code}", "تاریخ: {dispatched_at}"],
        "fields": ["carrier_name", "vehicle_plate", "driver_name"],
        "footer": "وزن کل: {total_weight_display}",
    },
}


class PrintService:
    """Manage print templates and render offline previews."""

    def __init__(self, db):
        self.db = db

    # -- templates ---------------------------------------------------------- #
    def create_template(self, code, name, document_type, template, actor="کاربر محلی"):
        """Store a new version of a template."""
        code, name = str(code or "").strip(), str(name or "").strip()
        document_type = str(document_type or "").strip()
        if not code or not name or not document_type:
            raise ValidationError("کد، نام و نوع سند قالب چاپ الزامی است.")
        if not isinstance(template, dict):
            raise ValidationError("قالب باید یک ساختار JSON باشد.")
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT COALESCE(MAX(version),0) FROM print_templates WHERE code=?",
                (code,)).fetchone()
            version = int(row[0]) + 1
            con.execute("UPDATE print_templates SET is_active=0 WHERE code=?", (code,))
            cur = con.execute(
                """INSERT INTO print_templates(code, name, document_type, version, is_active,
                        template_json, created_at, created_by)
                   VALUES(?,?,?,?,1,?,?,?)""",
                (code, name, document_type, version, json.dumps(template, ensure_ascii=False),
                 now_iso(), actor))
            self.db.audit(actor, "create_template", "print_template", cur.lastrowid,
                          "%s v%d" % (code, version), con)
            return {"id": cur.lastrowid, "code": code, "version": version}

    def list_templates(self, document_type=None, active_only=False):
        sql = "SELECT * FROM print_templates WHERE 1=1"
        params = []
        if document_type:
            sql += " AND document_type=?"
            params.append(document_type)
        if active_only:
            sql += " AND is_active=1"
        sql += " ORDER BY code, version DESC"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def activate_template(self, code, version, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT id FROM print_templates WHERE code=? AND version=?",
                (code, int(version))).fetchone()
            if not row:
                raise ValidationError("نسخهٔ قالب یافت نشد.")
            con.execute("UPDATE print_templates SET is_active=0 WHERE code=?", (code,))
            con.execute("UPDATE print_templates SET is_active=1 WHERE id=?", (row["id"],))
            self.db.audit(actor, "activate_template", "print_template", row["id"],
                          "%s v%s" % (code, version), con)
            return True

    # -- rendering ---------------------------------------------------------- #
    def render(self, document_type, payload, template_code=None, unit="تومان"):
        """Render a preview as plain text.  Fully offline, no fonts or drivers."""
        template = self._template_for(document_type, template_code)
        payload = dict(payload or {})
        payload.setdefault("unit", unit)
        for key, value in list(payload.items()):
            if key.endswith("_rial") and key != "unit":
                payload[key + "_display"] = format_money(int(value), unit)
        lines = []
        title = template.get("title", document_type)
        lines.append(str(title))
        lines.append("=" * max(20, len(str(title))))
        for header_line in template.get("header", []):
            lines.append(self._substitute(header_line, payload))
        lines.append("-" * 30)
        for field in template.get("fields", []):
            lines.append("%s: %s" % (field, self._substitute(str(payload.get(field, "")), payload)))
        for line in template.get("rows", []):
            lines.append(" | ".join(self._substitute(str(cell), payload) for cell in line))
        for footer_line in template.get("footer", []):
            lines.append(self._substitute(footer_line, payload))
        return {"title": title, "text": "\n".join(lines), "unit": unit,
                "template": template}

    def _template_for(self, document_type, template_code=None):
        if template_code:
            with self.db.reader() as con:
                row = con.execute(
                    """SELECT template_json FROM print_templates
                       WHERE code=? AND version=(SELECT MAX(version) FROM print_templates
                       WHERE code=?) AND is_active=1""",
                    (template_code, template_code)).fetchone()
            if not row:
                raise ValidationError("قالب چاپ یافت نشد: %s" % template_code)
            return json.loads(row["template_json"])
        with self.db.reader() as con:
            row = con.execute(
                """SELECT template_json FROM print_templates
                   WHERE document_type=? AND is_active=1 ORDER BY version DESC LIMIT 1""",
                (document_type,)).fetchone()
        if row:
            return json.loads(row["template_json"])
        template = DEFAULT_TEMPLATES.get(document_type)
        if template is None:
            raise ValidationError("قالب پیش‌فرضی برای این نوع سند تعریف نشده است.")
        return template

    @staticmethod
    def _substitute(text, payload):
        result = text
        for key, value in payload.items():
            result = result.replace("{%s}" % key, "" if value is None else str(value))
        return result

    def preview_documents(self, document_type, payloads, unit="تومان"):
        return [self.render(document_type, payload, unit=unit) for payload in payloads]
