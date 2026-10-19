# -*- coding: utf-8 -*-
"""Backup, verification and restore (Prompt 26).

A backup is a real SQLite copy created with the online backup API, so it is
consistent even while the application is running.  Every backup stores the
schema version and a SHA-256 checksum.  A restore is a two step operation:
``verify`` first (integrity + version + row counts), then the actual restore,
which always takes a safety copy of the live database before replacing it.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from datetime import datetime

from ..core import ConflictError, ValidationError, now_iso


def file_checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class BackupService:
    """Create, verify and restore local backups."""

    def __init__(self, db):
        self.db = db

    # -- create ------------------------------------------------------------- #
    def create(self, target_dir, actor="کاربر محلی"):
        """Create a consistent backup of the live database."""
        target_dir = os.path.abspath(target_dir)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = os.path.join(target_dir, "sorting_os-backup-%s.sqlite3" % stamp)
        source = sqlite3.connect(self.db.path)
        try:
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
        finally:
            source.close()
        checksum = file_checksum(target)
        version = self.db.schema_version()
        with self.db.transaction() as con:
            con.execute(
                """INSERT INTO settings(key, value, updated_at, updated_by) VALUES(?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                   updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
                ("last_backup", "%s|%s|%s" % (target, checksum, version), now_iso(), actor))
            self.db.audit(actor, "backup", "database", None,
                          "file=%s schema=%s sha256=%s" % (os.path.basename(target), version, checksum),
                          con)
        return {"path": target, "schema_version": version, "sha256": checksum,
                "size_bytes": os.path.getsize(target)}

    def list_backups(self, target_dir):
        if not os.path.isdir(target_dir):
            return []
        items = []
        for name in sorted(os.listdir(target_dir)):
            if not name.endswith(".sqlite3"):
                continue
            path = os.path.join(target_dir, name)
            items.append({"name": name, "path": path,
                          "size_bytes": os.path.getsize(path),
                          "modified_at": datetime.fromtimestamp(
                              os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")})
        return items

    # -- verify ------------------------------------------------------------- #
    def verify(self, path):
        """Check a backup file: exists, readable, integrity ok, version known."""
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            raise ValidationError("فایل backup یافت نشد: %s" % path)
        try:
            con = sqlite3.connect(path)
        except sqlite3.DatabaseError:
            return {"path": path, "integrity": "file is not a database", "schema_version": 0,
                    "sha256": file_checksum(path), "counts": {}, "is_valid": False}
        try:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            version = 0
            if "schema_meta" in tables:
                row = con.execute(
                    "SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                version = int(row[0]) if row else 0
            counts = {}
            for table in ("parties", "shipments", "invoices", "journal_entries"):
                if table in tables:
                    counts[table] = con.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
        except sqlite3.DatabaseError:
            return {"path": path, "integrity": "file is not a database", "schema_version": 0,
                    "sha256": file_checksum(path), "counts": {}, "is_valid": False}
        finally:
            con.close()
        return {"path": path, "integrity": integrity, "schema_version": version,
                "sha256": file_checksum(path), "counts": counts,
                "is_valid": integrity == "ok"}

    # -- restore ------------------------------------------------------------ #
    def restore(self, path, actor="کاربر محلی", safety_dir=None):
        """Restore a backup over the live database.

        A safety copy of the current database is taken first; the operation
        refuses to continue when the backup does not pass verification.
        """
        report = self.verify(path)
        if not report["is_valid"]:
            raise ConflictError("فایل backup سالم نیست: %s" % report["integrity"])
        safety_dir = safety_dir or os.path.join(os.path.dirname(self.db.path), "backups")
        if not os.path.isdir(safety_dir):
            os.makedirs(safety_dir)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safety = os.path.join(safety_dir, "pre-restore-%s.sqlite3" % stamp)
        if os.path.exists(self.db.path):
            shutil.copy2(self.db.path, safety)
        self.db.close() if hasattr(self.db, "close") else None
        shutil.copy2(report["path"], self.db.path)
        with self.db.transaction() as con:
            self.db.audit(actor, "restore", "database", None,
                          "from=%s sha256=%s safety=%s"
                          % (os.path.basename(report["path"]), report["sha256"],
                             os.path.basename(safety)), con)
        return {"restored_from": report["path"], "safety_copy": safety,
                "schema_version": report["schema_version"], "sha256": report["sha256"]}
