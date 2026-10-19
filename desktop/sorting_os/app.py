# -*- coding: utf-8 -*-
"""Application shell for SORTING OS (Prompt 05).

Responsibilities of the shell — and of nothing else:

* resolve the local data paths (never the current working directory);
* load the local configuration;
* configure local logging;
* open the database and run the versioned migrations;
* wire the domain services (single composition root);
* provide an error boundary and a graceful shutdown path;
* expose version information and a couple of headless maintenance commands so
  that the installation can be checked without a GUI.

The shell knows nothing about accounting rules: every rule lives in
``sorting_os.services``.
"""
from __future__ import annotations

import argparse
import atexit
import logging
import os
import sys
import traceback

from . import __version__
from .config import AppConfig
from .db import AppDatabase
from .logging_setup import setup_logging
from .paths import AppPaths

DEFAULT_ACTOR = "کاربر محلی"


class ServiceRegistry:
    """Composition root: one instance of every domain service."""

    #: service attribute name -> module inside ``sorting_os.services``
    SERVICE_MAP = (
        ("parties", "PartyService"),
        ("catalog", "CatalogService"),
        ("operations", "OperationsService"),
        ("documents", "DocumentService"),
        ("ledger", "LedgerService"),
        ("settlement", "SettlementService"),
        ("banking", "BankingService"),
        ("auth", "AuthService"),
        ("exchange", "ExchangeService"),
        ("reporting", "ReportService"),
        ("backup", "BackupService"),
        ("printing", "PrintService"),
        ("periods", "PeriodService"),
    )

    def __init__(self, db, actor=DEFAULT_ACTOR):
        import importlib

        self.db = db
        self.actor = actor
        self.missing = []
        # every service takes the database only; the actor is passed per call
        for attribute, class_name in self.SERVICE_MAP:
            try:
                module = importlib.import_module("." + attribute, "sorting_os.services")
                setattr(self, attribute, getattr(module, class_name)(db))
            except (ImportError, AttributeError) as exc:
                # a partially migrated checkout must still start
                self.missing.append("%s (%s)" % (class_name, exc))
                setattr(self, attribute, None)

    def names(self):
        return sorted(name for name, _ in self.SERVICE_MAP
                      if getattr(self, name, None) is not None)


class Application:
    """The shell itself.  Usable head-less (tests, maintenance) and with GUI."""

    def __init__(self, paths=None, db_path=None, actor=DEFAULT_ACTOR,
                 console_logging=True):
        self.paths = (paths or AppPaths.resolve()).ensure()
        self.config = AppConfig.load(self.paths.config_file)
        self.log_level = self.config.get("log_level", "INFO")
        self.logger = setup_logging(self.paths.log_file, level=self.log_level,
                                    console=console_logging)
        self.logger.info("SORTING OS %s — data dir: %s", __version__, self.paths.home)
        self.actor = actor
        self._db = None
        self._services = None
        self._db_path = db_path or self.paths.db_file

    # -- lazily created collaborators --------------------------------------- #
    @property
    def db(self):
        if self._db is None:
            self._db = AppDatabase(self._db_path, actor=self.actor)
        return self._db

    @property
    def services(self):
        if self._services is None:
            self._services = ServiceRegistry(self.db, actor=self.actor)
        return self._services

    # -- lifecycle ---------------------------------------------------------- #
    def shutdown(self):
        """Graceful shutdown: close the database and flush the log."""
        if self._db is not None:
            try:
                self._db.close()
            except Exception:  # pragma: no cover - defensive
                self.logger.exception("خطا در بستن پایگاه داده")
            self._db = None
        logging.shutdown()
        self.logger.info("خروج کنترل‌شده انجام شد.")

    def install_signal_handlers(self):
        def handler(signum, frame):  # pragma: no cover - interactive path
            self.logger.info("دریافت سیگنال %s — خاموش‌سازی", signum)
            self.shutdown()
            sys.exit(0)

        for name in ("SIGINT", "SIGTERM"):
            sig = getattr(__import__("signal"), name, None)
            if sig is not None:
                try:
                    __import__("signal").signal(sig, handler)
                except (ValueError, OSError):  # pragma: no cover - non main thread
                    pass
        atexit.register(self.shutdown)

    # -- diagnostics -------------------------------------------------------- #
    def version_info(self):
        return {
            "app": "SORTING OS",
            "version": __version__,
            "python": sys.version.split()[0],
            "data_dir": self.paths.home,
            "database": self._db_path,
            "schema_version": self.db.schema_version(),
            "services": self.services.names(),
            "open_decisions": self.config.open_decisions(),
        }

    def doctor(self):
        """Integrity and configuration check that can run without a GUI."""
        integrity = self.db.integrity_check()
        counts = self.db.table_counts()
        return {
            "data_dir": self.paths.home,
            "database": self._db_path,
            "schema_version": self.db.schema_version(),
            "integrity": integrity,
            "table_counts": counts,
            "config": self.config.as_dict(),
            "open_decisions": self.config.open_decisions(),
        }

    # -- commands ----------------------------------------------------------- #
    def run_gui(self):
        """Start the desktop UI (Prompt 24).  Requires tkinter."""
        from .ui.app import launch

        return launch(self)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sorting-os",
        description="SORTING OS — نرم‌افزار محلی سورتینگ و حسابداری (اجرای آفلاین)")
    parser.add_argument("--version", action="store_true", help="نمایش نسخه و مسیر داده")
    parser.add_argument("--init-db", action="store_true", help="ساخت/ارتقای پایگاه داده")
    parser.add_argument("--doctor", action="store_true", help="بررسی سلامت پایگاه داده")
    parser.add_argument("--data-dir", help="مسیر داده (پیش‌فرض: مسیر محلی سیستم‌عامل)")
    parser.add_argument("--no-console-log", action="store_true", help="فقط ثبت در فایل")
    parser.add_argument("--gui", action="store_true", help="اجرای رابط گرافیکی (پیش‌فرض)")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)

    paths = AppPaths.resolve(args.data_dir).ensure()
    app = Application(paths=paths, console_logging=not args.no_console_log)

    try:
        if args.version:
            info = app.version_info()
            for key, value in info.items():
                print("%s: %s" % (key, value))
            return 0
        if args.init_db:
            print("پایگاه داده: %s" % app.db.path)
            print("نسخهٔ schema: %s" % app.db.schema_version())
            return 0
        if args.doctor:
            report = app.doctor()
            for key, value in report.items():
                print("%s: %s" % (key, value))
            return 0
        return app.run_gui()
    except Exception:
        app.logger.error("خطایUnhandled در پوستهٔ برنامه:\n%s",
                         traceback.format_exc())
        sys.stderr.write("خطای داخلی ثبت شد؛ جزئیات در %s\n" % app.paths.log_file)
        return 1
    finally:
        app.shutdown()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
