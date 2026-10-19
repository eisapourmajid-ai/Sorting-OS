# -*- coding: utf-8 -*-
"""Settlement (صافی) engine - versioned, auditable and free of hidden rules.

The engine implements the formula of ``docs/03-accounting-settlement-rules.md``:

    NetSettlement = ReferenceGrossAmount + ApprovedAdditions - ApprovedDiscounts
                    - Commission - ChargeableExpenses + ApprovedAdjustments

Two calculation modes are supported and the mode is stored with the result,
so it is always visible what the operator entered:

* ``net_rate_input``    - the operator enters the net *rate*;
* ``net_amount_input``  - the operator enters the net *amount* and the rate is
  derived from it.

Commission and deduction rules are versioned rows with a validity window: a
rule change today never changes a settlement that was approved yesterday.
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso, to_rial

#: Version of the settlement formula.  Bump together with a test update.
FORMULA_VERSION = "settlement-v1"

MODES = ("net_amount_input", "net_rate_input")
ADJUSTMENT_TYPES = ("discount", "addition", "expense", "shortage", "other")


def round_rial(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class SettlementService:
    """Versioned settlement calculation with a stored calculation snapshot."""

    def __init__(self, db):
        self.db = db

    # -- rules -------------------------------------------------------------- #
    def create_rule(self, code, name, kind, method, basis, rate_percent=None, amount_rial=None,
                    scope="shipment", cap_rial=None, floor_rial=None, payer_party_id=None,
                    valid_from=None, valid_to=None, notes=None, actor="کاربر محلی"):
        """Create a versioned commission/deduction rule."""
        if kind not in ("commission", "deduction", "addition"):
            raise ValidationError("نوع قاعده نامعتبر است: %s" % kind)
        if method not in ("percent", "fixed"):
            raise ValidationError("روش قاعده نامعتبر است: %s" % method)
        if basis not in ("gross", "net", "contract"):
            raise ValidationError("مبنای قاعده نامعتبر است: %s" % basis)
        if method == "percent":
            if rate_percent is None:
                raise ValidationError("برای قاعده درصدی، نرخ لازم است.")
            if float(rate_percent) < 0:
                raise ValidationError("نرخ نمی‌تواند منفی باشد.")
        else:
            amount_rial = to_rial(amount_rial or 0, "ریال", "مبلغ ثابت قاعده")
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM settlement_rules WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد قاعده تکراری است: %s" % code)
            cur = con.execute(
                """INSERT INTO settlement_rules(code, name, kind, method, basis, scope,
                        rate_percent, amount_rial, cap_rial, floor_rial, payer_party_id,
                        valid_from, valid_to, is_active, notes, created_at, created_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                (str(code).strip(), str(name).strip(), kind, method, basis, scope,
                 float(rate_percent) if rate_percent is not None else None, amount_rial,
                 cap_rial, floor_rial, payer_party_id,
                 normalize_iso_date(valid_from or now_iso()[:10], "تاریخ شروع قاعده"),
                 valid_to, str(notes or "").strip() or None, now_iso(), actor))
            self.db.audit(actor, "create", "settlement_rule", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_rules(self, on_date=None, active_only=True):
        sql = "SELECT * FROM settlement_rules WHERE 1=1"
        params = []
        if active_only:
            sql += " AND is_active=1"
        if on_date:
            on_date = normalize_iso_date(on_date, "تاریخ")
            sql += " AND valid_from <= ? AND (valid_to IS NULL OR valid_to >= ?)"
            params.extend([on_date, on_date])
        sql += " ORDER BY code"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    # -- calculation -------------------------------------------------------- #
    def calculate(self, party_id, shipment_id, lines, calculation_mode, reference_amount_rial=None,
                  net_rate_percent=None, net_amount_rial=None, adjustments=None,
                  settlement_date=None, actor="کاربر محلی"):
        """Calculate a settlement and store it with a full calculation snapshot."""
        if calculation_mode not in MODES:
            raise ValidationError("حالت محاسبه نامعتبر است: %s" % calculation_mode)
        if not lines:
            raise ValidationError("حداقل یک ردیف صافی لازم است.")
        settlement_date = normalize_iso_date(settlement_date or now_iso()[:10], "تاریخ صافی")
        prepared_lines = []
        gross_total = 0
        for index, line in enumerate(lines, 1):
            dispatched = float(line.get("dispatched_weight_kg", 0) or 0)
            declared = line.get("declared_weight_kg")
            declared = float(declared) if declared is not None else None
            unit_price = to_rial(line.get("unit_price", 0), line.get("unit", "ریال"), "قیمت واحد")
            basis = line.get("basis", "dispatched")
            if basis not in ("dispatched", "declared", "contract"):
                raise ValidationError("مبنای وزن صافی نامعتبر است: %s" % basis)
            if basis == "declared" and declared is None:
                raise ValidationError("برای مبنای «اعلامی» وزن اعلامی لازم است.")
            if basis == "contract":
                contract_weight = float(line.get("contract_weight_kg", 0) or 0)
            else:
                contract_weight = 0.0
            weight = {"dispatched": dispatched, "declared": declared or 0.0,
                      "contract": contract_weight}[basis]
            gross = round_rial(Decimal(str(weight)) * Decimal(unit_price))
            prepared_lines.append({
                "product_id": line.get("product_id"),
                "grade_id": line.get("grade_id"),
                "packaging_id": line.get("packaging_id"),
                "dispatched_weight_kg": dispatched,
                "declared_weight_kg": declared,
                "unit_price_rial": unit_price,
                "gross_amount_rial": gross,
                "line_total_rial": gross,
                "basis": basis,
            })
            gross_total += gross

        reference = int(reference_amount_rial) if reference_amount_rial is not None else gross_total
        if reference < 0:
            raise ValidationError("مبلغ مبنا نمی‌تواند منفی باشد.")

        if calculation_mode == "net_rate_input":
            if net_rate_percent is None:
                raise ValidationError("در حالت ورود درصد، نرخ خالص لازم است.")
            rate = Decimal(str(net_rate_percent))
            if rate < 0:
                raise ValidationError("نرخ خالص نمی‌تواند منفی باشد.")
            net_amount = round_rial(Decimal(reference) * rate / Decimal(100))
            net_rate = rate
        else:
            if net_amount_rial is None:
                raise ValidationError("در حالت ورود مبلغ، مبلغ خالص لازم است.")
            net_amount = to_rial(net_amount_rial, "ریال", "مبلغ خالص")
            net_rate = (Decimal(net_amount) * Decimal(100) / Decimal(reference)) \
                if reference > 0 else None

        commission = 0
        applied_rules = []
        for rule in self.list_rules(on_date=settlement_date):
            if rule["kind"] != "commission":
                continue
            if rule["method"] == "percent":
                base = {"gross": gross_total, "net": net_amount,
                        "contract": reference}[rule["basis"]]
                amount = round_rial(Decimal(base) * Decimal(str(rule["rate_percent"])) / Decimal(100))
            else:
                amount = int(rule["amount_rial"] or 0)
            if rule["cap_rial"] is not None:
                amount = min(amount, int(rule["cap_rial"]))
            if rule["floor_rial"] is not None:
                amount = max(amount, int(rule["floor_rial"]))
            commission += amount
            applied_rules.append({"code": rule["code"], "amount_rial": amount,
                                  "basis": rule["basis"], "method": rule["method"]})

        additions = 0
        deductions = 0
        adjustment_rows = []
        for adjustment in (adjustments or []):
            amount = to_rial(adjustment.get("amount_rial", 0), "ریال", "مبلغ تعدیل")
            atype = adjustment.get("adjustment_type", "other")
            if atype not in ADJUSTMENT_TYPES:
                raise ValidationError("نوع تعدیل نامعتبر است: %s" % atype)
            if atype in ("discount", "expense", "shortage"):
                deductions += amount
            else:
                additions += amount
            adjustment_rows.append({"adjustment_type": atype, "amount_rial": amount,
                                    "reason": adjustment.get("reason"),
                                    "basis": adjustment.get("basis")})

        # The declared net amount is the base of the settlement; commission and
        # approved adjustments are then deducted/added (docs/03 section 6).
        net_settlement = net_amount + additions - deductions - commission
        if net_settlement < 0:
            raise ValidationError("نتیجه صافی منفی است؛ ورودی‌ها را بازبینی کنید.")

        payload = {
            "formula_version": FORMULA_VERSION,
            "calculation_mode": calculation_mode,
            "reference_amount_rial": reference,
            "net_rate_percent": float(net_rate) if net_rate is not None else None,
            "net_amount_rial": net_amount,
            "commission_rial": commission,
            "additions_rial": additions,
            "deductions_rial": deductions,
            "net_settlement_rial": net_settlement,
            "rules_applied": applied_rules,
            "adjustments": adjustment_rows,
            "gross_lines_rial": gross_total,
        }
        stamp = now_iso()
        with self.db.transaction() as con:
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM settlements").fetchone()
            code = "STL-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO settlements(code, party_id, shipment_id, calculation_mode,
                        reference_amount_rial, net_rate_percent, net_amount_rial,
                        commission_rial, deductions_rial, additions_rial, formula_version,
                        status, payload_json, created_at, created_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?, 'draft', ?,?,?)""",
                (code, party_id, shipment_id, calculation_mode, reference,
                 float(net_rate) if net_rate is not None else None, net_amount, commission,
                 deductions, additions, FORMULA_VERSION, json.dumps(payload, ensure_ascii=False),
                 stamp, actor))
            settlement_id = cur.lastrowid
            for line in prepared_lines:
                con.execute(
                    """INSERT INTO settlement_lines(settlement_id, product_id, grade_id, packaging_id,
                            dispatched_weight_kg, declared_weight_kg, unit_price_rial,
                            gross_amount_rial, line_total_rial, basis, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (settlement_id, line["product_id"], line["grade_id"], line["packaging_id"],
                     line["dispatched_weight_kg"], line["declared_weight_kg"],
                     line["unit_price_rial"], line["gross_amount_rial"], line["line_total_rial"],
                     line["basis"], stamp))
            for adjustment in adjustment_rows:
                con.execute(
                    """INSERT INTO settlement_adjustments(settlement_id, adjustment_type,
                            amount_rial, basis, reason, source_type, source_id, status,
                            created_at, created_by)
                       VALUES(?,?,?,?,?,?,?, 'approved', ?,?)""",
                    (settlement_id, adjustment["adjustment_type"], adjustment["amount_rial"],
                     adjustment.get("basis"), adjustment.get("reason"), None, None, stamp, actor))
            self.db.audit(actor, "calculate", "settlement", settlement_id,
                          "%s; net=%d rial" % (code, net_settlement), con)
            return {"settlement_id": settlement_id, "code": code, "payload": payload}

    # -- workflow ----------------------------------------------------------- #
    def approve(self, settlement_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM settlements WHERE id=?", (settlement_id,)).fetchone()
            if not row:
                raise ValidationError("صافی یافت نشد.")
            if row["status"] == "posted":
                raise ConflictError("صافی posting‌شده قابل تأیید مجدد نیست.")
            con.execute("UPDATE settlements SET status='approved', approved_by=?, approved_at=?"
                        " WHERE id=?", (actor, now_iso(), settlement_id))
            self.db.audit(actor, "approve", "settlement", settlement_id, row["code"], con)
            return True

    def cancel(self, settlement_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM settlements WHERE id=?", (settlement_id,)).fetchone()
            if not row:
                raise ValidationError("صافی یافت نشد.")
            if row["posted_entry_id"]:
                raise ConflictError("صافی posting‌شده ابتدا باید برگردانده شود.")
            con.execute("UPDATE settlements SET status='cancelled' WHERE id=?", (settlement_id,))
            self.db.audit(actor, "cancel", "settlement", settlement_id, row["code"], con)
            return True

    def get(self, settlement_id):
        with self.db.reader() as con:
            head = con.execute(
                """SELECT s.*, p.display_name AS party_name FROM settlements s
                   JOIN parties p ON p.id=s.party_id WHERE s.id=?""", (settlement_id,)).fetchone()
            if not head:
                return None
            lines = con.execute("SELECT * FROM settlement_lines WHERE settlement_id=? ORDER BY id",
                                (settlement_id,)).fetchall()
            adjustments = con.execute(
                "SELECT * FROM settlement_adjustments WHERE settlement_id=? ORDER BY id",
                (settlement_id,)).fetchall()
        result = dict(head)
        result["lines"] = [dict(l) for l in lines]
        result["adjustments"] = [dict(a) for a in adjustments]
        if result.get("payload_json"):
            result["payload"] = json.loads(result["payload_json"])
        return result

    def list_settlements(self, party_id=None, status=None, limit=200):
        sql = "SELECT s.*, p.display_name AS party_name FROM settlements s JOIN parties p ON p.id=s.party_id"
        params = []
        if party_id:
            sql += " WHERE s.party_id=?"
            params.append(party_id)
        elif status:
            sql += " WHERE s.status=?"
            params.append(status)
        sql += " ORDER BY s.id DESC LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def post_settlement(self, settlement_id, actor="کاربر محلی", ledger=None):
        """Post the settlement result to the ledger (provisional until the
        commercial model of DEC-001/DEC-003 is approved)."""
        settlement = self.get(settlement_id)
        if not settlement:
            raise ValidationError("صافی یافت نشد.")
        if settlement["status"] != "approved":
            raise ConflictError("فقط صافی تأییدشده قابل posting است.")
        if ledger is None:
            from .ledger import LedgerService

            ledger = LedgerService(self.db)
        amount = int(settlement["net_amount_rial"])
        if amount <= 0:
            raise ValidationError("مبلغ خالص صافی باید بزرگ‌تر از صفر باشد.")
        notes = ["مدل کارمزدی/امانی و مبنای درصد صافی هنوز تصویب نشده است (DEC-001/DEC-003)."]
        lines = [
            {"account_code": "1100", "debit_rial": amount, "credit_rial": 0,
             "description": "طلب بابت صافی", "party_ref": str(settlement["party_id"])},
            {"account_code": "4000", "debit_rial": 0, "credit_rial": amount,
             "description": "درآمد صافی/خدمات"},
        ]
        description = "صافی %s - %s | %s" % (settlement["code"], settlement["party_name"],
                                              " ".join(notes))
        entry_id, created = ledger._post(settlement_date := (settlement.get("approved_at")
                                                             or now_iso())[:10],
                                         description, lines, "settlement", settlement_id, actor)
        if created:
            with self.db.transaction() as con:
                con.execute("UPDATE settlements SET posted_entry_id=?, status='posted' WHERE id=?",
                            (entry_id, settlement_id))
                self.db.audit(actor, "post", "settlement", settlement_id,
                              "entry=%s amount=%d rial" % (entry_id, amount), con)
        return {"entry_id": entry_id, "created": created, "provisional": True, "notes": notes}
