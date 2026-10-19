# -*- coding: utf-8 -*-
"""Product, grade and packaging master data (Prompt 09).

``Product`` (پرتقال), ``Grade`` (درجه یک) and ``PackagingType`` (سبد ۱۰ کیلویی)
are separate entities on purpose: "پرتقال درجه یک در سبد ۱۰ کیلویی" must not
collapse into one indivisible SKU in every table.
"""
from __future__ import annotations

from ..core import ConflictError, ValidationError, now_iso


class CatalogService:
    """Master data for products, grades and packaging types."""

    def __init__(self, db):
        self.db = db

    # -- products ----------------------------------------------------------- #
    def create_product(self, code, name, category=None, base_unit="کیلوگرم",
                       notes=None, actor="کاربر محلی"):
        code, name = str(code or "").strip(), str(name or "").strip()
        if not code or not name:
            raise ValidationError("کد و نام محصول الزامی است.")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM products WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد محصول تکراری است: %s" % code)
            cur = con.execute(
                """INSERT INTO products(code,name,category,base_unit,is_active,notes,created_at,created_by)
                   VALUES(?,?,?,?,1,?,?,?)""",
                (code, name, str(category or "").strip() or None, base_unit or "کیلوگرم",
                 str(notes or "").strip() or None, now_iso(), actor))
            self.db.audit(actor, "create", "product", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_products(self, active_only=True):
        sql = "SELECT * FROM products"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY name COLLATE NOCASE"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql).fetchall()]

    def get_product(self, product_id):
        with self.db.reader() as con:
            row = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return dict(row) if row else None

    def deactivate_product(self, product_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            con.execute("UPDATE products SET is_active=0 WHERE id=?", (product_id,))
            self.db.audit(actor, "deactivate", "product", product_id, "", con)
            return True

    # -- grades ------------------------------------------------------------- #
    def create_grade(self, code, name, sort_order=0, actor="کاربر محلی"):
        code, name = str(code or "").strip(), str(name or "").strip()
        if not code or not name:
            raise ValidationError("کد و نام درجه الزامی است.")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM grades WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد درجه تکراری است: %s" % code)
            cur = con.execute(
                "INSERT INTO grades(code,name,sort_order,is_active) VALUES(?,?,?,1)",
                (code, name, int(sort_order)))
            self.db.audit(actor, "create", "grade", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_grades(self, active_only=True):
        sql = "SELECT * FROM grades"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY sort_order, name COLLATE NOCASE"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql).fetchall()]

    # -- packaging ---------------------------------------------------------- #
    def create_packaging(self, code, name, reference_weight_kg=None, count_unit="سبد",
                         actor="کاربر محلی"):
        code, name = str(code or "").strip(), str(name or "").strip()
        if not code or not name:
            raise ValidationError("کد و نام بسته‌بندی الزامی است.")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM packaging_types WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد بسته‌بندی تکراری است: %s" % code)
            cur = con.execute(
                """INSERT INTO packaging_types(code,name,reference_weight_kg,count_unit,is_active)
                   VALUES(?,?,?,?,1)""",
                (code, name, reference_weight_kg, count_unit or "سبد"))
            self.db.audit(actor, "create", "packaging", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_packaging(self, active_only=True):
        sql = "SELECT * FROM packaging_types"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY name COLLATE NOCASE"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql).fetchall()]

    # -- rules -------------------------------------------------------------- #
    def add_packaging_rule(self, product_id, packaging_id, grade_id=None, valid_from=None,
                            actor="کاربر محلی"):
        with self.db.transaction() as con:
            cur = con.execute(
                """INSERT INTO product_packaging_rules(product_id, grade_id, packaging_id,
                                                       valid_from, is_active)
                   VALUES(?,?,?,?,1)""",
                (product_id, grade_id, packaging_id, (valid_from or now_iso()[:10])))
            self.db.audit(actor, "create", "packaging_rule", cur.lastrowid, "", con)
            return cur.lastrowid

    def allowed_packaging(self, product_id, grade_id=None, on_date=None):
        """Packaging types allowed for a product/grade on a given date."""
        on_date = on_date or now_iso()[:10]
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT p.* FROM packaging_types p
                   JOIN product_packaging_rules r ON r.packaging_id = p.id
                   WHERE r.product_id=? AND r.is_active=1
                     AND (r.grade_id IS NULL OR r.grade_id=?)
                     AND r.valid_from <= ? AND (r.valid_to IS NULL OR r.valid_to >= ?)""",
                (product_id, grade_id, on_date, on_date)).fetchall()
        return [dict(r) for r in rows]

    def describe_line(self, product_id, grade_id, packaging_id):
        """Human readable product/grade/packaging description for documents."""
        product = self.get_product(product_id) if product_id else None
        with self.db.reader() as con:
            grade = con.execute("SELECT * FROM grades WHERE id=?", (grade_id,)).fetchone() \
                if grade_id else None
            packaging = con.execute("SELECT * FROM packaging_types WHERE id=?", (packaging_id,)).fetchone() \
                if packaging_id else None
        parts = []
        if product:
            parts.append(product["name"])
        if grade:
            parts.append(grade["name"])
        if packaging:
            parts.append(packaging["name"])
        return " - ".join(parts)
