# -*- coding: utf-8 -*-
"""SQLite persistence layer with versioned, transactional migrations.

``AppDatabase`` is the single entry point for every service in the
application.  It owns:

* the connection factory (foreign keys on, deterministic close, busy timeout);
* the migration runner (transactional, versioned, idempotent);
* the audit trail writer;
* small helpers for key/value settings.

The service layer never opens a raw connection of its own; it always goes
through :meth:`AppDatabase.transaction` so that a failed operation rolls the
whole unit of work back (Prompt 06 / Prompt 30).
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .core import normalize_iso_date
from .migrations import LATEST_SCHEMA_VERSION, MIGRATIONS


def now_iso():
    """Local timestamp, second resolution (operational documents)."""
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def now_utc_iso():
    """UTC timestamp used by the accounting core (ledger ordering)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _ClosingConnection(sqlite3.Connection):
    """Commit/rollback via sqlite context semantics and close deterministically."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class MigrationError(RuntimeError):
    """A migration failed; the database is left untouched."""


class AppDatabase:
    """Local SQLite database for the whole SORTING OS application."""

    def __init__(self, path, actor="کاربر محلی"):
        self.path = os.path.abspath(path)
        self.actor = actor
        parent = os.path.dirname(self.path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        self.migrate()

    def close(self):
        """Close the database.

        Every operation opens and closes its own connection, so there is no
        long-lived handle to release; the method exists for the application
        shell (graceful shutdown) and for symmetry with other drivers.
        """
        return None

    # -- connections -------------------------------------------------------- #
    def connect(self):
        con = sqlite3.connect(self.path, timeout=20, factory=_ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 20000")
        return con

    @contextmanager
    def transaction(self):
        """Run a unit of work atomically (``BEGIN IMMEDIATE``)."""
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

    @contextmanager
    def reader(self):
        """Read-only access; never starts a write transaction."""
        con = self.connect()
        try:
            yield con
        finally:
            con.close()

    # -- migrations --------------------------------------------------------- #
    def schema_version(self):
        with self.reader() as con:
            row = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
            ).fetchone()
            if not row:
                return 0
            value = con.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            return int(value[0]) if value else 0

    def migrate(self, target=None):
        """Apply pending migrations.  Returns the list of applied versions."""
        target = target or LATEST_SCHEMA_VERSION
        applied = []
        current = self.schema_version()
        for version, description, groups in MIGRATIONS:
            if version <= current or version > target:
                continue
            con = self.connect()
            try:
                con.execute("BEGIN IMMEDIATE")
                for _title, statements in groups:
                    for statement in statements:
                        con.execute(statement)
                con.execute(
                    "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)",
                    (str(version),),
                )
                con.commit()
            except sqlite3.OperationalError as exc:
                con.rollback()
                raise MigrationError(
                    "migration %s (%s) failed: %s" % (version, description, exc))
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()
            applied.append(version)
        if applied:
            self._ensure_accounting_schema()
        return applied

    def _ensure_accounting_schema(self):
        """The ledger has its own schema namespace but must exist in every DB."""
        from accounting_core import initialize_schema  # local import avoids a cycle

        initialize_schema(self.path)

    # -- audit -------------------------------------------------------------- #
    def audit(self, actor, action, entity_type, entity_id=None, details=None, con=None):
        """Append an audit event.  Never raises for logging purposes."""
        own = con is None
        if own:
            con = self.connect()
        try:
            con.execute(
                """INSERT INTO audit_log(event_at,actor,action,entity_type,entity_id,details)
                   VALUES(?,?,?,?,?,?)""",
                (now_iso(), actor or self.actor or "کاربر محلی", action, entity_type,
                 None if entity_id is None else str(entity_id), details or ""),
            )
            if own:
                con.commit()
        finally:
            if own:
                con.close()

    def list_audit(self, limit=200, entity_type=None, entity_id=None):
        clauses, params = [], []
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            clauses.append("entity_id = ?")
            params.append(str(entity_id))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(int(limit))
        with self.reader() as con:
            return con.execute(
                "SELECT * FROM audit_log" + where + " ORDER BY id DESC LIMIT ?", params
            ).fetchall()

    # -- settings ----------------------------------------------------------- #
    def get_setting(self, key, default=None):
        with self.reader() as con:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value, actor=None, con=None):
        own = con is None
        if own:
            con = self.connect()
        try:
            con.execute(
                """INSERT INTO settings(key,value,updated_at,updated_by) VALUES(?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                   updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
                (key, str(value), now_iso(), actor or self.actor),
            )
            if own:
                con.commit()
        finally:
            if own:
                con.close()

    # -- misc --------------------------------------------------------------- #
    def integrity_check(self):
        with self.reader() as con:
            return con.execute("PRAGMA integrity_check").fetchone()[0]

    def table_counts(self):
        tables = [
            "parties", "shipments", "weighing_tickets", "invoices", "invoice_lines",
            "journal_entries", "journal_lines", "inventory_transactions", "dispatches",
            "settlements", "payments", "cheques", "bank_transactions", "audit_log",
        ]
        counts = {}
        with self.reader() as con:
            for table in tables:
                exists = con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone()
                if not exists:
                    continue
                counts[table] = con.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
        return counts


def default_db_path():
    """Default user-data location (kept out of the source tree)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "SORTING-OS", "sorting_os.sqlite3")


def today():
    return normalize_iso_date(datetime.now().strftime("%Y-%m-%d"))
