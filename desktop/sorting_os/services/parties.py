# -*- coding: utf-8 -*-
"""Party master data, roles, identity matching and safe merge (Prompts 07-08).

Rules that are not negotiable:

* one physical party may hold several roles (owner, customer, supplier,
  carrier, worker) - roles live in ``party_roles``;
* parties with a similar name are **never** merged automatically.  The service
  only produces *suggestions* with a score and a reason, and a human decides;
* a merge never deletes data: the source party is deactivated, all references
  are re-pointed to the target and every step is written to the audit trail.
"""
from __future__ import annotations

import difflib
import re

from ..core import ConflictError, ValidationError, normalize_iso_date, now_iso

#: Roles used by the domain.  ``owner`` = مالک کالا, ``customer`` = خریدار ...
ROLE_CODES = {
    "owner": "مالک کالا",
    "customer": "خریدار",
    "supplier": "تأمین‌کننده",
    "carrier": "حامل",
    "worker": "کارگر/پیمانکار",
    "bank": "بانک",
    "other": "سایر",
}

_PUNCTUATION = re.compile(r"[\s‌ً-ْٰ«»\"'()\[\]{}\-_.,،؛:!؟/\\]+")


def normalize_name(value):
    """Normalised key used for similarity comparison (never for merging)."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = _PUNCTUATION.sub(" ", text)
    return " ".join(text.split())


def similarity(left, right):
    """0..1 similarity of two names (difflib, offline)."""
    a, b = normalize_name(left), normalize_name(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 4)


class PartyService:
    """CRUD, roles, matching and merge for parties."""

    def __init__(self, db):
        self.db = db

    # -- helpers ------------------------------------------------------------ #
    def _next_code(self, con):
        row = con.execute("SELECT COALESCE(MAX(id), 0) FROM parties").fetchone()
        return "PTY-%06d" % (int(row[0]) + 1)

    @staticmethod
    def _normalize_roles(roles):
        if roles is None:
            return []
        if isinstance(roles, str):
            roles = [roles]
        result = []
        for role in roles:
            text = str(role or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    # -- CRUD --------------------------------------------------------------- #
    def create(self, display_name, phone=None, national_id=None, address=None,
               roles=("owner",), legal_name=None, notes=None, actor="کاربر محلی"):
        """Create a party.  Duplicate national ids are rejected, never merged."""
        name = str(display_name or "").strip()
        if not name:
            raise ValidationError("نام شخص الزامی است.")
        national_id = str(national_id or "").strip() or None
        phone = str(phone or "").strip() or None
        role_list = self._normalize_roles(roles)
        stamp = now_iso()
        with self.db.transaction() as con:
            if national_id:
                hit = con.execute(
                    "SELECT id, display_name FROM parties WHERE national_id=? AND is_active=1",
                    (national_id,),
                ).fetchone()
                if hit:
                    raise ConflictError(
                        "کد ملی برای «%s» ثبت شده است؛ ادغام خودکار انجام نشد."
                        % hit["display_name"])
            code = self._next_code(con)
            labels = "، ".join(ROLE_CODES.get(role, role) for role in role_list) or "سایر"
            cur = con.execute(
                """INSERT INTO parties(code, display_name, phone, national_id, address, roles,
                                      legal_name, notes, is_active, created_at, updated_at,
                                      created_by, updated_by, normalized_name)
                   VALUES(?,?,?,?,?,?,?,?,1,?,?,?,?,?)""",
                (code, name, phone, national_id, str(address or "").strip(),
                 labels, str(legal_name or "").strip() or None,
                 str(notes or "").strip() or None, stamp, stamp, actor, actor,
                 normalize_name(name)),
            )
            party_id = cur.lastrowid
            for role in role_list or ["other"]:
                self._insert_role(con, party_id, role, stamp, actor)
            self.db.audit(actor, "create", "party", party_id, name, con)
            return party_id

    def update(self, party_id, display_name=None, phone=None, national_id=None,
               address=None, legal_name=None, notes=None, actor="کاربر محلی"):
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone()
            if not row:
                raise ValidationError("شخص یافت نشد.")
            name = str(display_name if display_name is not None else row["display_name"]).strip()
            if not name:
                raise ValidationError("نام شخص الزامی است.")
            nid = national_id if national_id is not None else row["national_id"]
            nid = str(nid or "").strip() or None
            if nid:
                hit = con.execute(
                    "SELECT id, display_name FROM parties WHERE national_id=? AND id<>?",
                    (nid, party_id)).fetchone()
                if hit:
                    raise ConflictError(
                        "کد ملی برای «%s» ثبت شده است؛ ادغام خودکار انجام نشد."
                        % hit["display_name"])
            con.execute(
                """UPDATE parties SET display_name=?, phone=?, national_id=?, address=?,
                       legal_name=?, notes=?, updated_at=?, updated_by=?, normalized_name=?
                   WHERE id=?""",
                (name,
                 phone if phone is not None else row["phone"],
                 nid,
                 address if address is not None else row["address"],
                 legal_name if legal_name is not None else row["legal_name"],
                 notes if notes is not None else row["notes"],
                 now_iso(), actor, normalize_name(name), party_id),
            )
            self.db.audit(actor, "update", "party", party_id, name, con)
            return party_id

    def deactivate(self, party_id, actor="کاربر محلی"):
        """Deactivate (never delete) a party that still has history."""
        with self.db.transaction() as con:
            row = con.execute("SELECT display_name FROM parties WHERE id=?", (party_id,)).fetchone()
            if not row:
                raise ValidationError("شخص یافت نشد.")
            con.execute("UPDATE parties SET is_active=0, updated_at=?, updated_by=? WHERE id=?",
                        (now_iso(), actor, party_id))
            self.db.audit(actor, "deactivate", "party", party_id, row["display_name"], con)
            return True

    def get(self, party_id):
        with self.db.reader() as con:
            row = con.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone()
        return dict(row) if row else None

    def search(self, text="", active_only=True, limit=200):
        sql = "SELECT * FROM parties WHERE 1=1"
        params = []
        if active_only:
            sql += " AND is_active=1"
        needle = str(text or "").strip()
        if needle:
            like = "%" + needle + "%"
            sql += (" AND (display_name LIKE ? OR phone LIKE ? OR national_id LIKE ?"
                    " OR code LIKE ? OR normalized_name LIKE ?)")
            params.extend([like, like, like, like, "%" + normalize_name(needle) + "%"])
        sql += " ORDER BY display_name COLLATE NOCASE LIMIT ?"
        params.append(int(limit))
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def list_all(self, active_only=True):
        sql = "SELECT * FROM parties"
        if active_only:
            sql += " WHERE is_active=1"
        sql += " ORDER BY display_name COLLATE NOCASE"
        with self.db.reader() as con:
            return [dict(r) for r in con.execute(sql).fetchall()]

    # -- roles -------------------------------------------------------------- #
    def _insert_role(self, con, party_id, role_code, stamp, actor):
        code = role_code if role_code in ROLE_CODES else "other"
        con.execute(
            """INSERT OR IGNORE INTO party_roles(party_id, role_code, valid_from, is_active,
                                                 created_at, created_by)
               VALUES(?,?,?,1,?,?)""",
            (party_id, code, stamp[:10], stamp, actor))

    def add_role(self, party_id, role_code, valid_from=None, valid_to=None, actor="کاربر محلی"):
        if role_code not in ROLE_CODES:
            raise ValidationError("نقش نامعتبر است: %s" % role_code)
        start = normalize_iso_date(valid_from or now_iso()[:10], "تاریخ شروع نقش")
        with self.db.transaction() as con:
            con.execute(
                """INSERT OR IGNORE INTO party_roles(party_id, role_code, valid_from, valid_to,
                                                     is_active, created_at, created_by)
                   VALUES(?,?,?,?,1,?,?)""",
                (party_id, role_code, start, valid_to, now_iso(), actor))
            self.db.audit(actor, "add_role", "party", party_id, role_code, con)
            return True

    def roles(self, party_id):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT role_code, valid_from, valid_to FROM party_roles
                   WHERE party_id=? AND is_active=1 ORDER BY role_code""", (party_id,)).fetchall()
        return [dict(r) for r in rows]

    # -- identity matching -------------------------------------------------- #
    def find_candidates(self, display_name, phone=None, national_id=None, exclude_id=None,
                        threshold=0.55):
        """Return *suggested* duplicates.  Never merges anything."""
        target_nid = str(national_id or "").strip()
        target_phone = str(phone or "").strip()
        suggestions = []
        for party in self.search(display_name, active_only=True, limit=500):
            if exclude_id and party["id"] == exclude_id:
                continue
            score = 0.0
            reasons = []
            if target_nid and (party["national_id"] or "").strip() == target_nid:
                score = 1.0
                reasons.append("کد ملی یکسان")
            else:
                name_score = similarity(display_name, party["display_name"])
                if name_score >= threshold:
                    score = name_score
                    reasons.append("تشابه نام %.0f%%" % (name_score * 100))
                if target_phone and (party["phone"] or "").strip() == target_phone:
                    score = max(score, 0.9)
                    reasons.append("تلفن یکسان")
            if score > 0:
                suggestions.append({
                    "party": party,
                    "score": round(score, 4),
                    "reason": "، ".join(reasons) or "تشابه احتمالی",
                })
        suggestions.sort(key=lambda item: item["score"], reverse=True)
        return suggestions

    def enqueue_match(self, source_party_id, candidate_party_id, score, reason,
                      actor="کاربر محلی"):
        with self.db.transaction() as con:
            con.execute(
                """INSERT OR IGNORE INTO party_match_queue(source_party_id, candidate_party_id,
                                                            score, reason, status, created_at)
                   VALUES(?,?,?,?,'open',?)""",
                (source_party_id, candidate_party_id, float(score), str(reason), now_iso()))
            self.db.audit(actor, "match_suggest", "party", source_party_id,
                          "candidate=%s score=%.2f" % (candidate_party_id, score), con)
            return True

    def review_queue(self, status="open"):
        with self.db.reader() as con:
            rows = con.execute(
                """SELECT q.*, s.display_name AS source_name, c.display_name AS candidate_name
                   FROM party_match_queue q
                   JOIN parties s ON s.id = q.source_party_id
                   JOIN parties c ON c.id = q.candidate_party_id
                   WHERE q.status = ? ORDER BY q.score DESC, q.id""", (status,)).fetchall()
        return [dict(r) for r in rows]

    def decide_match(self, queue_id, decision, actor="کاربر محلی"):
        """``decision`` is ``merged`` or ``dismissed``."""
        if decision not in ("merged", "dismissed"):
            raise ValidationError("تصمیم نامعتبر است.")
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM party_match_queue WHERE id=?", (queue_id,)).fetchone()
            if not row:
                raise ValidationError("مورد صف تطبیق یافت نشد.")
            con.execute(
                """UPDATE party_match_queue SET status=?, decided_by=?, decided_at=?
                   WHERE id=?""",
                (decision, actor, now_iso(), queue_id))
            self.db.audit(actor, decision, "party_match", queue_id, row["reason"], con)
            return True

    # -- merge -------------------------------------------------------------- #
    #: Tables whose foreign key points at a party.  Merging re-points them.
    PARTY_REFERENCES = (
        ("parties", "owner_party_id"),
        ("parties", "delivering_party_id"),
        ("shipments", "owner_party_id"),
        ("shipments", "delivering_party_id"),
        ("weighing_tickets", "shipment_id"),
        ("invoices", "party_id"),
        ("invoice_lines", "shipment_id"),
        ("settlements", "party_id"),
        ("settlements", "shipment_id"),
        ("payments", "party_id"),
        ("cheques", "party_id"),
        ("expenses", "party_id"),
        ("dispatches", "carrier_party_id"),
        ("dispatch_lines", "shipment_id"),
        ("shipment_lines", "shipment_id"),
        ("sorting_operations", "shipment_id"),
        ("inventory_transactions", "shipment_id"),
        ("party_roles", "party_id"),
        ("party_aliases", "party_id"),
        ("party_match_queue", "source_party_id"),
        ("party_match_queue", "candidate_party_id"),
        ("inventory_reservations", "party_id"),
    )

    def merge(self, source_party_id, target_party_id, actor="کاربر محلی"):
        """Merge ``source`` into ``target`` without losing history."""
        if source_party_id == target_party_id:
            raise ValidationError("ادغام یک شخص با خودش مجاز نیست.")
        with self.db.transaction() as con:
            source = con.execute("SELECT * FROM parties WHERE id=?", (source_party_id,)).fetchone()
            target = con.execute("SELECT * FROM parties WHERE id=?", (target_party_id,)).fetchone()
            if not source or not target:
                raise ValidationError("یکی از اشخاص یافت نشد.")
            moved = 0
            for table, column in self.PARTY_REFERENCES:
                if table == "parties":
                    continue
                try:
                    cur = con.execute(
                        "UPDATE %s SET %s=? WHERE %s=?" % (table, column, column),
                        (target_party_id, source_party_id))
                    moved += cur.rowcount or 0
                except Exception:
                    continue
            # keep the source as a searchable alias, then deactivate it
            con.execute(
                "INSERT OR IGNORE INTO party_aliases(party_id, alias_text, alias_type, created_at)"
                " VALUES(?,?,'نام ادغام‌شده',?)",
                (target_party_id, source["display_name"], now_iso()))
            con.execute(
                "UPDATE parties SET is_active=0, updated_at=?, updated_by=? WHERE id=?",
                (now_iso(), actor, source_party_id))
            con.execute(
                """INSERT INTO party_merge_log(merged_party_id, target_party_id, actor, merged_at, details)
                   VALUES(?,?,?,?,?)""",
                (source_party_id, target_party_id, actor, now_iso(),
                 "rows moved: %d" % moved))
            self.db.audit(actor, "merge", "party", source_party_id,
                          "merged into %s (%s); rows moved: %d"
                          % (target_party_id, target["display_name"], moved), con)
            return {"moved_rows": moved, "target_party_id": target_party_id}

    def party_balance(self, party_id):
        """Outstanding balance from the posted ledger (never a manual number)."""
        with self.db.reader() as con:
            row = con.execute(
                """SELECT COALESCE(SUM(l.debit_rial),0) AS debit, COALESCE(SUM(l.credit_rial),0) AS credit
                   FROM journal_lines l JOIN journal_entries e ON e.id=l.entry_id
                   WHERE l.party_ref=? AND e.status='posted'""",
                (str(party_id),)).fetchone()
        debit, credit = int(row["debit"]), int(row["credit"])
        return {"debit_rial": debit, "credit_rial": credit, "balance_rial": debit - credit}
