# -*- coding: utf-8 -*-
"""Users, roles, granular permissions and a tamper-evident audit chain.

The application is offline-first: there is no cloud login, no telemetry and no
mandatory online licence (Prompt 25).  Access control is therefore local and
role based, and every sensitive operation is written to an audit trail whose
entries are hash-chained so that a later modification of a row can be detected.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from ..core import ConflictError, PermissionDenied, ValidationError, now_iso

#: PBKDF2 rounds - high enough to make an offline dictionary attack costly.
PBKDF2_ROUNDS = 60000

#: Default roles seeded on first start.
DEFAULT_ROLES = {
    "admin": ("مدیر سیستم", [
        "party.read", "party.write", "party.merge", "catalog.write", "operations.write",
        "invoice.write", "ledger.post", "settlement.approve", "settlement.post",
        "bank.reconcile", "cheque.write", "data.import", "data.export", "report.view",
        "print.manage", "backup.manage", "user.manage", "period.close", "audit.view"]),
    "manager": ("مدیر مجموعه", [
        "party.read", "party.write", "party.merge", "catalog.write", "operations.write",
        "invoice.write", "settlement.approve", "data.import", "data.export", "report.view",
        "print.manage", "audit.view"]),
    "operator": ("اپراتور", [
        "party.read", "catalog.read", "operations.write", "invoice.write", "report.view",
        "data.export"]),
    "accountant": ("حسابدار", [
        "party.read", "invoice.write", "ledger.post", "settlement.approve", "settlement.post",
        "bank.reconcile", "cheque.write", "report.view", "data.import", "data.export",
        "print.manage", "audit.view", "period.close"]),
    "viewer": ("مشاهده‌گر", ["party.read", "report.view"]),
}

ALL_PERMISSIONS = sorted({p for _, perms in DEFAULT_ROLES.values() for p in perms})


def hash_password(password, salt=None, rounds=PBKDF2_ROUNDS):
    """Return ``(hash_hex, salt_hex)`` for a plaintext password."""
    if not password or len(str(password)) < 6:
        raise ValidationError("گذرواژه باید حداقل ۶ نویسه باشد.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt, rounds)
    return digest.hex(), salt.hex()


def verify_password(password, hash_hex, salt_hex, rounds=PBKDF2_ROUNDS):
    """Constant-time password check."""
    try:
        salt = bytes.fromhex(salt_hex)
    except (TypeError, ValueError):
        return False
    candidate, _ = hash_password(password, salt, rounds)
    return hmac.compare_digest(candidate, hash_hex or "")


class Actor:
    """The authenticated user performing an operation."""

    def __init__(self, user_id=None, username="کاربر محلی", roles=(), permissions=()):
        self.user_id = user_id
        self.username = username
        self.roles = list(roles)
        self.permissions = set(permissions)

    def can(self, permission):
        return permission in self.permissions

    def require(self, permission):
        if not self.can(permission):
            raise PermissionDenied(
                "کاربر «%s» مجوز «%s» را ندارد." % (self.username, permission))
        return True

    def __repr__(self):  # pragma: no cover - debugging helper
        return "Actor(%s, roles=%s)" % (self.username, self.roles)


class AuthService:
    """Local user management, permissions and the audit chain."""

    def __init__(self, db):
        self.db = db
        self._seed_roles()

    def _seed_roles(self):
        with self.db.transaction() as con:
            for code, (name, permissions) in DEFAULT_ROLES.items():
                con.execute(
                    "INSERT OR IGNORE INTO roles(code, name, description) VALUES(?,?,?)",
                    (code, name, "نقش پیش‌فرض"))
                for permission in permissions:
                    con.execute(
                        "INSERT OR IGNORE INTO role_permissions(role_code, permission) VALUES(?,?)",
                        (code, permission))

    # -- users -------------------------------------------------------------- #
    def create_user(self, username, password, full_name=None, role_code="operator",
                    is_active=True, actor="کاربر محلی"):
        username = str(username or "").strip()
        if not username:
            raise ValidationError("نام کاربری الزامی است.")
        if role_code not in DEFAULT_ROLES:
            raise ValidationError("نقش نامعتبر است: %s" % role_code)
        password_hash, salt = hash_password(password)
        with self.db.transaction() as con:
            if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                raise ConflictError("نام کاربری تکراری است: %s" % username)
            cur = con.execute(
                """INSERT INTO users(username, full_name, role_code, password_hash, salt, is_active,
                        created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (username, str(full_name or "").strip() or None, role_code, password_hash, salt,
                 int(bool(is_active)), now_iso()))
            con.execute("INSERT OR IGNORE INTO user_roles(user_id, role_code) VALUES(?,?)",
                        (cur.lastrowid, role_code))
            self.db.audit(actor, "create_user", "user", cur.lastrowid, username, con)
            return cur.lastrowid

    def set_password(self, user_id, password, actor="کاربر محلی"):
        password_hash, salt = hash_password(password)
        with self.db.transaction() as con:
            cur = con.execute(
                "UPDATE users SET password_hash=?, salt=? WHERE id=?", (password_hash, salt, user_id))
            if not cur.rowcount:
                raise ValidationError("کاربر یافت نشد.")
            self.db.audit(actor, "set_password", "user", user_id, "", con)
            return True

    def set_user_roles(self, user_id, roles, actor="کاربر محلی"):
        roles = [r for r in (roles or []) if r in DEFAULT_ROLES]
        if not roles:
            raise ValidationError("حداقل یک نقش لازم است.")
        with self.db.transaction() as con:
            con.execute("DELETE FROM user_roles WHERE user_id=?", (user_id,))
            for role in roles:
                con.execute("INSERT OR IGNORE INTO user_roles(user_id, role_code) VALUES(?,?)",
                            (user_id, role))
            con.execute("UPDATE users SET role_code=? WHERE id=?", (roles[0], user_id))
            self.db.audit(actor, "set_roles", "user", user_id, ",".join(roles), con)
            return True

    def list_users(self):
        with self.db.reader() as con:
            rows = con.execute(
                "SELECT id, username, full_name, role_code, is_active, created_at, last_login_at"
                " FROM users ORDER BY username").fetchall()
        return [dict(r) for r in rows]

    # -- sessions ----------------------------------------------------------- #
    def authenticate(self, username, password):
        """Return an :class:`Actor` or ``None``.  Failed attempts are audited."""
        username = str(username or "").strip()
        with self.db.reader() as con:
            row = con.execute(
                "SELECT * FROM users WHERE username=? AND is_active=1", (username,)).fetchone()
        if not row:
            self.db.audit(username or "ناشناس", "login_failed", "user", None, "کاربر ناموجود")
            return None
        if not verify_password(password, row["password_hash"], row["salt"]):
            self.db.audit(username, "login_failed", "user", row["id"], "گذرواژه نادرست")
            return None
        with self.db.transaction() as con:
            roles = [r[0] for r in con.execute(
                "SELECT role_code FROM user_roles WHERE user_id=?", (row["id"],)).fetchall()]
            permissions = set()
            for role in roles:
                permissions.update(r[0] for r in con.execute(
                    "SELECT permission FROM role_permissions WHERE role_code=?", (role,)).fetchall())
            con.execute("UPDATE users SET last_login_at=? WHERE id=?", (now_iso(), row["id"]))
        self.db.audit(username, "login", "user", row["id"], ",".join(roles))
        return Actor(user_id=row["id"], username=row["username"], roles=roles,
                     permissions=permissions)

    def actor_for(self, username):
        """Build an actor without a password check (e.g. local single-user mode)."""
        with self.db.reader() as con:
            row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if not row:
                return Actor(username=username)
            roles = [r[0] for r in con.execute(
                "SELECT role_code FROM user_roles WHERE user_id=?", (row["id"],)).fetchall()]
            permissions = set()
            for role in roles:
                permissions.update(r[0] for r in con.execute(
                    "SELECT permission FROM role_permissions WHERE role_code=?", (role,)).fetchall())
        return Actor(user_id=row["id"], username=row["username"], roles=roles,
                     permissions=permissions)

    # -- audit chain -------------------------------------------------------- #
    @staticmethod
    def _entry_hash(prev_hash, event_at, actor, action, entity_type, entity_id, details):
        payload = "\x1f".join([
            prev_hash or "", event_at or "", actor or "", action or "",
            entity_type or "", str(entity_id or ""), details or ""])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append_audit(self, actor, action, entity_type, entity_id=None, details=None):
        """Append a hash-chained audit event."""
        with self.db.transaction() as con:
            row = con.execute(
                "SELECT entry_hash FROM audit_log WHERE entry_hash IS NOT NULL"
                " ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = row[0] if row else None
            stamp = now_iso()
            entry_hash = self._entry_hash(prev_hash, stamp, actor, action, entity_type,
                                          entity_id, details)
            con.execute(
                """INSERT INTO audit_log(event_at, actor, action, entity_type, entity_id, details,
                        prev_hash, entry_hash)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (stamp, actor or "کاربر محلی", action, entity_type,
                 None if entity_id is None else str(entity_id), details or "",
                 prev_hash, entry_hash))
            return entry_hash

    def verify_audit_chain(self):
        """Verify the hash chain and report the first broken entry (if any)."""
        with self.db.reader() as con:
            rows = con.execute(
                "SELECT id, event_at, actor, action, entity_type, entity_id, details,"
                " prev_hash, entry_hash FROM audit_log WHERE entry_hash IS NOT NULL"
                " ORDER BY id").fetchall()
        prev_hash = None
        for row in rows:
            expected = self._entry_hash(prev_hash, row["event_at"], row["actor"], row["action"],
                                        row["entity_type"], row["entity_id"], row["details"])
            if (row["prev_hash"] or "") != (prev_hash or "") or expected != row["entry_hash"]:
                return {"valid": False, "checked": len(rows), "broken_at": row["id"]}
            prev_hash = row["entry_hash"]
        return {"valid": True, "checked": len(rows), "broken_at": None}

    def chain_existing_audit(self, actor="کاربر محلی"):
        """Backfill the hash chain for entries written before the chain existed."""
        with self.db.transaction() as con:
            rows = con.execute(
                "SELECT id, event_at, actor, action, entity_type, entity_id, details"
                " FROM audit_log WHERE entry_hash IS NULL ORDER BY id").fetchall()
            prev = con.execute(
                "SELECT entry_hash FROM audit_log WHERE entry_hash IS NOT NULL"
                " ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = prev[0] if prev else None
            for row in rows:
                entry_hash = self._entry_hash(prev_hash, row["event_at"], row["actor"],
                                              row["action"], row["entity_type"],
                                              row["entity_id"], row["details"])
                con.execute("UPDATE audit_log SET prev_hash=?, entry_hash=? WHERE id=?",
                            (prev_hash, entry_hash, row["id"]))
                prev_hash = entry_hash
        return {"chained": len(rows)}
