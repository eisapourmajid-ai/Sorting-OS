# -*- coding: utf-8 -*-
"""Operational core: shipments, weighing, sorting, inventory and dispatch.

Physical facts and financial facts stay separate here (Prompt 12/13/14):

* weighing a basket is a *measurement*, not an accounting event;
* a sorting operation consumes an input and produces graded outputs, waste and
  loss - the mass balance is enforced explicitly;
* the inventory ledger is event based: every movement is a row in
  ``inventory_transactions`` and the balance is always derived from it.  There
  is no editable "stock number" anywhere;
* every movement is idempotent through
  ``UNIQUE(source_type, source_id, source_line_id, purpose)``.
"""
from __future__ import annotations

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso

SHIPMENT_STATES = ("received", "weighed", "sorted", "stored", "dispatched", "closed")
OWNERSHIP_MODELS = ("undetermined", "service", "consignment", "buy_sell")


class OperationsService:
    """Shipments, weighing tickets, sorting runs, inventory and dispatch."""

    def __init__(self, db):
        self.db = db

    # -- shipments ---------------------------------------------------------- #
    def create_shipment(self, owner_party_id, product_name=None, weight_kg=0,
                        received_at=None, ownership_model="undetermined", contract_ref=None,
                        delivering_party_id=None, lines=None, notes=None,
                        actor="کاربر محلی"):
        """Create an incoming shipment.  Ownership is never assumed (DEC-002)."""
        if ownership_model not in OWNERSHIP_MODELS:
            raise ValidationError("مدل مالکیت نامعتبر است: %s" % ownership_model)
        product_name = str(product_name or "").strip()
        lines = lines or []
        if not product_name and not lines:
            raise ValidationError("نام محصول یا اقلام محموله الزامی است.")
        try:
            weight_kg = float(weight_kg or 0)
        except (TypeError, ValueError):
            raise ValidationError("وزن باید عدد باشد.")
        if weight_kg < 0:
            raise ValidationError("وزن نمی‌تواند منفی باشد.")
        stamp = now_iso()
        received_at = normalize_iso_date(received_at or stamp[:10], "تاریخ دریافت")
        with self.db.transaction() as con:
            owner = con.execute(
                "SELECT id FROM parties WHERE id=? AND is_active=1", (owner_party_id,)).fetchone()
            if not owner:
                raise ValidationError("مالک انتخاب‌شده معتبر یا فعال نیست.")
            if delivering_party_id is not None:
                if not con.execute("SELECT 1 FROM parties WHERE id=? AND is_active=1",
                                   (delivering_party_id,)).fetchone():
                    raise ValidationError("طرف تحویل‌دهنده معتبر یا فعال نیست.")
            row = con.execute(
                "SELECT COALESCE(MAX(id),0) FROM shipments").fetchone()
            code = "SHP-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO shipments(code, owner_party_id, delivering_party_id, product_name,
                                        received_weight, received_at, status, current_state,
                                        ownership_model, contract_ref, notes, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, owner_party_id, delivering_party_id, product_name or "چندمحصولی",
                 weight_kg, received_at, "دریافت‌شده", "received", ownership_model,
                 str(contract_ref or "").strip() or None, str(notes or "").strip() or None,
                 stamp, stamp))
            shipment_id = cur.lastrowid
            for line in lines:
                self._insert_shipment_line(con, shipment_id, line, stamp)
            self.db.audit(actor, "create", "shipment", shipment_id, code, con)
            return shipment_id

    def _insert_shipment_line(self, con, shipment_id, line, stamp):
        weight = float(line.get("weight_kg", 0) or 0)
        if weight < 0:
            raise ValidationError("وزن ردیف نمی‌تواند منفی باشد.")
        con.execute(
            """INSERT INTO shipment_lines(shipment_id, product_id, grade_id, packaging_id,
                                          description, quantity, unit, weight_kg, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (shipment_id, line.get("product_id"), line.get("grade_id"), line.get("packaging_id"),
             str(line.get("description") or "").strip() or None,
             float(line.get("quantity", 0) or 0), line.get("unit") or "کیلوگرم", weight, stamp))

    def list_shipments(self, state=None, owner_id=None, limit=200):
        clauses, params = [], []
        if state:
            clauses.append("s.current_state = ?")
            params.append(state)
        if owner_id:
            clauses.append("s.owner_party_id = ?")
            params.append(owner_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(int(limit))
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT s.*, p.display_name AS owner_name
                   FROM shipments s JOIN parties p ON p.id = s.owner_party_id""" + where +
                " ORDER BY s.id DESC LIMIT ?", params).fetchall()
        return [dict(r) for r in rows]

    def get_shipment(self, shipment_id):
        with self.db.reader() as con:
            row = con.execute(
                """SELECT s.*, p.display_name AS owner_name FROM shipments s
                   JOIN parties p ON p.id=s.owner_party_id WHERE s.id=?""", (shipment_id,)).fetchone()
            lines = con.execute(
                "SELECT * FROM shipment_lines WHERE shipment_id=? ORDER BY id", (shipment_id,)).fetchall()
        if not row:
            return None
        result = dict(row)
        result["lines"] = [dict(l) for l in lines]
        return result

    def set_shipment_state(self, shipment_id, state, actor="کاربر محلی"):
        if state not in SHIPMENT_STATES:
            raise ValidationError("وضعیت محموله نامعتبر است: %s" % state)
        with self.db.transaction() as con:
            cur = con.execute(
                "UPDATE shipments SET current_state=?, status=?, updated_at=? WHERE id=?",
                (state, state, now_iso(), shipment_id))
            if not cur.rowcount:
                raise ValidationError("محموله یافت نشد.")
            self.db.audit(actor, "state_change", "shipment", shipment_id, state, con)
            return True

    # -- weighing ----------------------------------------------------------- #
    def create_weighing(self, ticket_type, gross_weight, tare_weight, shipment_ids=None,
                        vehicle_plate="", driver_name="", weighed_at=None, operator="",
                        notes="", actor="کاربر محلی"):
        """Record a weighing ticket.  ``gross >= tare`` is mandatory."""
        try:
            gross = float(gross_weight)
            tare = float(tare_weight)
        except (TypeError, ValueError):
            raise ValidationError("وزن‌ها باید عدد باشند.")
        if gross < 0 or tare < 0:
            raise ValidationError("وزن‌ها نمی‌توانند منفی باشند.")
        if gross < tare:
            raise ValidationError("وزن ناخالص نمی‌تواند کمتر از وزن خالی باشد.")
        net = round(gross - tare, 3)
        stamp = now_iso()
        weighed_at = normalize_iso_date(weighed_at or stamp[:10], "تاریخ توزین")
        with self.db.transaction() as con:
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM weighing_tickets").fetchone()
            code = "WGH-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO weighing_tickets(code, ticket_type, shipment_id, vehicle_plate,
                        driver_name, gross_weight, tare_weight, net_weight, weighed_at,
                        operator_name, notes, created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code, ticket_type, (shipment_ids or [None])[0] if shipment_ids else None,
                 str(vehicle_plate or "").strip(), str(driver_name or "").strip(),
                 gross, tare, net, weighed_at, str(operator or "").strip(),
                 str(notes or "").strip() or None, stamp))
            ticket_id = cur.lastrowid
            for shipment_id in (shipment_ids or []):
                if not con.execute("SELECT 1 FROM shipments WHERE id=?", (shipment_id,)).fetchone():
                    raise ValidationError("محموله انتخاب‌شده وجود ندارد.")
                con.execute(
                    "INSERT OR REPLACE INTO weighing_ticket_shipments"
                    "(weighing_ticket_id, shipment_id, weight_kg) VALUES(?,?,?)",
                    (ticket_id, shipment_id, net))
            self.db.audit(actor, "create", "weighing_ticket", ticket_id,
                          "%s; net=%.3f" % (code, net), con)
            return ticket_id

    def list_weighings(self, limit=200):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT w.*, s.code AS shipment_code FROM weighing_tickets w
                   LEFT JOIN shipments s ON s.id=w.shipment_id
                   ORDER BY w.id DESC LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    # -- sorting ------------------------------------------------------------ #
    def create_sorting_operation(self, shipment_id, input_weight_kg, output_lines,
                                 waste_weight_kg=0, loss_weight_kg=0, difference_weight_kg=0,
                                 measured_at=None, operator="", notes="", actor="کاربر محلی"):
        """Create a sorting run.

        Mass balance (docs/03 section 3.2):
            input = sum(output) + waste + registered loss + explained difference
        """
        try:
            input_weight = float(input_weight_kg)
        except (TypeError, ValueError):
            raise ValidationError("وزن ورودی باید عدد باشد.")
        if input_weight < 0:
            raise ValidationError("وزن ورودی نمی‌تواند منفی باشد.")
        waste = float(waste_weight_kg or 0)
        loss = float(loss_weight_kg or 0)
        difference = float(difference_weight_kg or 0)
        if waste < 0 or loss < 0:
            raise ValidationError("وزن افت/کسری نمی‌تواند منفی باشد.")
        # The line breakdown and the explicit parameters must not contradict each
        # other: the lines win, the parameter is only the default.
        totals = {"output": 0.0, "waste": 0.0, "loss": 0.0, "difference": 0.0}
        for line in output_lines:
            line_type = line.get("line_type", "output")
            if line_type not in totals:
                raise ValidationError("نوع ردیف سورتینگ نامعتبر است: %s" % line_type)
            totals[line_type] += float(line.get("weight_kg", 0) or 0)
        for key, parameter in (("waste", waste), ("loss", loss), ("difference", difference)):
            if totals[key] and parameter and abs(totals[key] - parameter) > 0.001:
                raise ValidationError(
                    "وزن %s در ردیف‌ها و پارامتر عملیات یکسان نیست (%.3f در برابر %.3f)."
                    % (key, totals[key], parameter))
            if not totals[key]:
                totals[key] = parameter
        output_total = totals["output"]
        expected = round(output_total + totals["waste"] + totals["loss"] + totals["difference"], 3)
        if abs(expected - round(input_weight, 3)) > 0.001:
            raise ValidationError(
                "تراز جرم برقرار نیست: ورودی %.3f در برابر مجموع خروجی/افت/کسری/اختلاف %.3f"
                % (input_weight, expected))
        stamp = now_iso()
        measured_at = normalize_iso_date(measured_at or stamp[:10], "تاریخ سورتینگ")
        with self.db.transaction() as con:
            if not con.execute("SELECT 1 FROM shipments WHERE id=?", (shipment_id,)).fetchone():
                raise ValidationError("محموله یافت نشد.")
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM sorting_operations").fetchone()
            code = "SRT-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO sorting_operations(code, shipment_id, input_weight_kg,
                        waste_weight_kg, loss_weight_kg, difference_weight_kg, measured_at,
                        operator, status, notes, created_at, created_by)
                   VALUES(?,?,?,?,?,?,?,?, 'draft', ?,?,?)""",
                (code, shipment_id, input_weight, totals["waste"], totals["loss"],
                 totals["difference"], measured_at,
                 str(operator or "").strip(), str(notes or "").strip() or None, stamp, actor))
            operation_id = cur.lastrowid
            for line in output_lines:
                line_type = line.get("line_type", "output")
                if line_type not in ("output", "waste", "loss", "difference"):
                    raise ValidationError("نوع ردیف سورتینگ نامعتبر است: %s" % line_type)
                con.execute(
                    """INSERT INTO sorting_output_lines(operation_id, line_type, product_id,
                            grade_id, packaging_id, weight_kg, package_count, description, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (operation_id, line_type, line.get("product_id"), line.get("grade_id"),
                     line.get("packaging_id"), float(line.get("weight_kg", 0) or 0),
                     int(line.get("package_count", 0) or 0),
                     str(line.get("description") or "").strip() or None, stamp))
            self.db.audit(actor, "create", "sorting_operation", operation_id, code, con)
            return operation_id

    def confirm_sorting_operation(self, operation_id, location_id=None, actor="کاربر محلی"):
        """Confirm a sorting run and post the inventory movements (idempotent)."""
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM sorting_operations WHERE id=?",
                              (operation_id,)).fetchone()
            if not row:
                raise ValidationError("عملیات سورتینگ یافت نشد.")
            if row["status"] == "confirmed":
                return {"already_confirmed": True, "entry_id": operation_id}
            if row["status"] == "cancelled":
                raise ConflictError("عملیات لغوشده قابل قطعی‌سازی نیست.")
            lines = con.execute(
                "SELECT * FROM sorting_output_lines WHERE operation_id=? ORDER BY id",
                (operation_id,)).fetchall()
            # consume the input
            self._post_inventory(con, movement_type="out", weight_kg=row["input_weight_kg"],
                                 shipment_id=row["shipment_id"], location_id=location_id,
                                 source_type="sorting", source_id=str(operation_id),
                                 source_line_id="input", purpose="consumption", actor=actor)
            for index, line in enumerate(lines, 1):
                # only graded output becomes stock; waste/loss stay documented on
                # the operation because they were already consumed as input.
                if line["line_type"] != "output":
                    continue
                self._post_inventory(
                    con, movement_type="in", weight_kg=line["weight_kg"],
                    product_id=line["product_id"], grade_id=line["grade_id"],
                    packaging_id=line["packaging_id"], shipment_id=row["shipment_id"],
                    location_id=location_id, source_type="sorting",
                    source_id=str(operation_id), source_line_id="line-%d" % index,
                    purpose="output", actor=actor)
            con.execute("UPDATE sorting_operations SET status='confirmed' WHERE id=?",
                        (operation_id,))
            con.execute("UPDATE shipments SET current_state='sorted', status='سورت‌شده',"
                        " updated_at=? WHERE id=?", (now_iso(), row["shipment_id"]))
            self.db.audit(actor, "confirm", "sorting_operation", operation_id, row["code"], con)
            return {"already_confirmed": False, "entry_id": operation_id}

    def list_sorting_operations(self, shipment_id=None, limit=200):
        sql = ("SELECT o.*, s.code AS shipment_code FROM sorting_operations o"
               " JOIN shipments s ON s.id=o.shipment_id")
        params = []
        if shipment_id:
            sql += " WHERE o.shipment_id=?"
            params.append(shipment_id)
        sql += " ORDER BY o.id DESC LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def sorting_operation_detail(self, operation_id):
        with self.db.reader() as con:
            head = con.execute("SELECT * FROM sorting_operations WHERE id=?",
                               (operation_id,)).fetchone()
            if not head:
                return None
            lines = con.execute("SELECT * FROM sorting_output_lines WHERE operation_id=? ORDER BY id",
                                (operation_id,)).fetchall()
        result = dict(head)
        result["lines"] = [dict(l) for l in lines]
        return result

    # -- inventory ---------------------------------------------------------- #
    def create_location(self, code, name, kind="warehouse", actor="کاربر محلی"):
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM inventory_locations WHERE code=?", (code,)).fetchone():
                raise ConflictError("کد مکان تکراری است: %s" % code)
            cur = con.execute(
                "INSERT INTO inventory_locations(code,name,kind,is_active,created_at) VALUES(?,?,?,1,?)",
                (code, name, kind, now_iso()))
            self.db.audit(actor, "create", "inventory_location", cur.lastrowid, code, con)
            return cur.lastrowid

    def list_locations(self):
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM inventory_locations WHERE is_active=1 ORDER BY name").fetchall()]

    def _post_inventory(self, con, movement_type, weight_kg, source_type, source_id,
                        source_line_id, purpose, actor, shipment_id=None, product_id=None,
                        grade_id=None, packaging_id=None, location_id=None):
        """Insert an inventory movement.  The unique key makes it idempotent."""
        if movement_type not in ("in", "out"):
            raise ValidationError("نوع حرکت انبار نامعتبر است.")
        cur = con.execute(
            """INSERT OR IGNORE INTO inventory_transactions(event_at, movement_type, product_id,
                    grade_id, packaging_id, shipment_id, location_id, quantity, unit, weight_kg,
                    source_type, source_id, source_line_id, purpose, status, actor, created_at)
               VALUES(?,?,?,?,?,?,?,?, 'کیلوگرم', ?,?,?,?,?, 'posted', ?,?)""",
            (now_iso(), movement_type, product_id, grade_id, packaging_id, shipment_id,
             location_id, float(weight_kg or 0), float(weight_kg or 0), source_type, source_id,
             source_line_id, purpose, actor, now_iso()))
        return cur.rowcount > 0

    def post_inventory_movement(self, movement_type, weight_kg, source_type, source_id,
                                source_line_id="", purpose="manual", actor="کاربر محلی",
                                **kwargs):
        """Public, idempotent inventory movement API."""
        with self.db.transaction() as con:
            created = self._post_inventory(
                con, movement_type=movement_type, weight_kg=weight_kg,
                source_type=source_type, source_id=source_id,
                source_line_id=source_line_id, purpose=purpose, actor=actor, **kwargs)
            if created:
                self.db.audit(actor, "inventory_move", "inventory", source_id,
                              "%s %.3f kg" % (movement_type, float(weight_kg or 0)), con)
            return created

    def inventory_balance(self, product_id=None, grade_id=None, location_id=None):
        """Current stock derived from the movement ledger (never a stored number)."""
        clauses, params = ["status='posted'"], []
        if product_id:
            clauses.append("product_id=?")
            params.append(product_id)
        if grade_id:
            clauses.append("grade_id=?")
            params.append(grade_id)
        if location_id:
            clauses.append("location_id=?")
            params.append(location_id)
        with self.db.reader() as con:
            row = con.execute(
                """SELECT COALESCE(SUM(CASE WHEN movement_type='in' THEN weight_kg ELSE 0 END),0) AS in_kg,
                          COALESCE(SUM(CASE WHEN movement_type='out' THEN weight_kg ELSE 0 END),0) AS out_kg
                   FROM inventory_transactions WHERE """ + " AND ".join(clauses), params).fetchone()
            rows = con.execute(
                """SELECT product_id, grade_id, location_id,
                          COALESCE(SUM(CASE WHEN movement_type='in' THEN weight_kg ELSE 0 END),0)
                            - COALESCE(SUM(CASE WHEN movement_type='out' THEN weight_kg ELSE 0 END),0) AS balance_kg
                   FROM inventory_transactions WHERE """ + " AND ".join(clauses) +
                " GROUP BY product_id, grade_id, location_id"
                " ORDER BY product_id, grade_id", params).fetchall()
        return {"in_kg": float(row["in_kg"]), "out_kg": float(row["out_kg"]),
                "balance_kg": float(row["in_kg"]) - float(row["out_kg"]),
                "by_bucket": [dict(r) for r in rows]}

    def list_inventory_transactions(self, limit=200):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT t.*, s.code AS shipment_code FROM inventory_transactions t
                   LEFT JOIN shipments s ON s.id=t.shipment_id
                   ORDER BY t.id DESC LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    # -- reservations ------------------------------------------------------- #
    def reserve(self, shipment_id, product_id=None, grade_id=None, location_id=None,
                party_id=None, weight_kg=0, expires_at=None, actor="کاربر محلی"):
        with self.db.transaction() as con:
            cur = con.execute(
                """INSERT INTO inventory_reservations(shipment_id, product_id, grade_id, location_id,
                        party_id, quantity, weight_kg, status, expires_at, created_at, created_by)
                   VALUES(?,?,?,?,?,0,?, 'active', ?,?,?)""",
                (shipment_id, product_id, grade_id, location_id, party_id,
                 float(weight_kg or 0), expires_at, now_iso(), actor))
            self.db.audit(actor, "reserve", "inventory_reservation", cur.lastrowid, "", con)
            return cur.lastrowid

    def release_reservation(self, reservation_id, actor="کاربر محلی"):
        with self.db.transaction() as con:
            cur = con.execute(
                "UPDATE inventory_reservations SET status='released' WHERE id=? AND status='active'",
                (reservation_id,))
            if not cur.rowcount:
                raise ConflictError("رزرو فعال یافت نشد.")
            self.db.audit(actor, "release", "inventory_reservation", reservation_id, "", con)
            return True

    def list_reservations(self, status=None):
        sql = "SELECT * FROM inventory_reservations"
        params = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY id DESC"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    # -- dispatch ----------------------------------------------------------- #
    def create_dispatch(self, carrier_party_id=None, lines=None, vehicle_plate="",
                        driver_name="", dispatched_at=None, note="", actor="کاربر محلی"):
        """Create an outbound dispatch order (حواله خروج)."""
        lines = lines or []
        if not lines:
            raise ValidationError("حداقل یک ردیف حواله لازم است.")
        stamp = now_iso()
        dispatched_at = normalize_iso_date(dispatched_at or stamp[:10], "تاریخ ارسال")
        with self.db.transaction() as con:
            if carrier_party_id is not None and not con.execute(
                    "SELECT 1 FROM parties WHERE id=? AND is_active=1", (carrier_party_id,)).fetchone():
                raise ValidationError("حامل انتخاب‌شده معتبر یا فعال نیست.")
            row = con.execute("SELECT COALESCE(MAX(id),0) FROM dispatches").fetchone()
            code = "DSP-%06d" % (int(row[0]) + 1)
            cur = con.execute(
                """INSERT INTO dispatches(code, carrier_party_id, vehicle_plate, driver_name,
                        dispatched_at, status, note, created_at, created_by)
                   VALUES(?,?,?,?,?, 'draft', ?,?,?)""",
                (code, carrier_party_id, str(vehicle_plate or "").strip(),
                 str(driver_name or "").strip(), dispatched_at, str(note or "").strip() or None,
                 stamp, actor))
            dispatch_id = cur.lastrowid
            for line in lines:
                weight = float(line.get("weight_kg", 0) or 0)
                if weight < 0:
                    raise ValidationError("وزن ردیف حواله نمی‌تواند منفی باشد.")
                basis = line.get("billing_basis", "dispatched")
                if basis not in ("dispatched", "declared", "contract"):
                    raise ValidationError("مبنای وزن قابل صورتحساب نامعتبر است: %s" % basis)
                billing_weight = line.get("billing_weight_kg")
                if billing_weight is None:
                    billing_weight = weight
                con.execute(
                    """INSERT INTO dispatch_lines(dispatch_id, shipment_id, product_id, grade_id,
                            packaging_id, weight_kg, package_count, billing_weight_kg,
                            billing_basis, note, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (dispatch_id, line.get("shipment_id"), line.get("product_id"),
                     line.get("grade_id"), line.get("packaging_id"), weight,
                     int(line.get("package_count", 0) or 0), float(billing_weight), basis,
                     str(line.get("note") or "").strip() or None, stamp))
            self.db.audit(actor, "create", "dispatch", dispatch_id, code, con)
            return dispatch_id

    def confirm_dispatch(self, dispatch_id, actor="کاربر محلی"):
        """Confirm the dispatch: consume the stock and close the shipments."""
        with self.db.transaction() as con:
            head = con.execute("SELECT * FROM dispatches WHERE id=?", (dispatch_id,)).fetchone()
            if not head:
                raise ValidationError("حواله یافت نشد.")
            if head["status"] == "confirmed":
                return {"already_confirmed": True}
            if head["status"] == "cancelled":
                raise ConflictError("حواله لغوشده قابل قطعی‌سازی نیست.")
            lines = con.execute("SELECT * FROM dispatch_lines WHERE dispatch_id=? ORDER BY id",
                                (dispatch_id,)).fetchall()
            for index, line in enumerate(lines, 1):
                self._post_inventory(
                    con, movement_type="out", weight_kg=line["weight_kg"],
                    product_id=line["product_id"], grade_id=line["grade_id"],
                    packaging_id=line["packaging_id"], shipment_id=line["shipment_id"],
                    source_type="dispatch", source_id=str(dispatch_id),
                    source_line_id="line-%d" % index, purpose="dispatch", actor=actor)
                if line["shipment_id"]:
                    con.execute(
                        "UPDATE shipments SET current_state='dispatched', status='ارسال‌شده',"
                        " updated_at=? WHERE id=?", (now_iso(), line["shipment_id"]))
            con.execute("UPDATE dispatches SET status='confirmed' WHERE id=?", (dispatch_id,))
            self.db.audit(actor, "confirm", "dispatch", dispatch_id, head["code"], con)
            return {"already_confirmed": False}

    def list_dispatches(self, limit=200):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT d.*, p.display_name AS carrier_name FROM dispatches d
                   LEFT JOIN parties p ON p.id=d.carrier_party_id
                   ORDER BY d.id DESC LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def dispatch_detail(self, dispatch_id):
        with self.db.reader() as con:
            head = con.execute(
                """SELECT d.*, p.display_name AS carrier_name FROM dispatches d
                   LEFT JOIN parties p ON p.id=d.carrier_party_id WHERE d.id=?""",
                (dispatch_id,)).fetchone()
            if not head:
                return None
            lines = con.execute("SELECT * FROM dispatch_lines WHERE dispatch_id=? ORDER BY id",
                                (dispatch_id,)).fetchall()
        result = dict(head)
        result["lines"] = [dict(l) for l in lines]
        return result
