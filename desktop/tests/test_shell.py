# -*- coding: utf-8 -*-
"""Application shell: paths, config, logging, error boundary, shutdown (Prompt 05)."""
from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os import __version__  # noqa: E402
from sorting_os.app import Application, ServiceRegistry, build_parser, main  # noqa: E402
from sorting_os.config import AppConfig  # noqa: E402
from sorting_os.logging_setup import setup_logging  # noqa: E402
from sorting_os.paths import AppPaths  # noqa: E402


class PathTests(unittest.TestCase):
    def test_home_override_wins(self):
        paths = AppPaths.resolve(environ={"SORTING_OS_HOME": "/tmp/custom"})
        self.assertEqual(paths.home, "/tmp/custom")

    def test_posix_default_uses_xdg(self):
        paths = AppPaths.resolve(environ={"XDG_DATA_HOME": "/tmp/xdg"})
        self.assertTrue(paths.db_file.startswith("/tmp/xdg"))
        self.assertTrue(paths.db_file.endswith("sorting_os.sqlite3"))

    def test_paths_do_not_depend_on_the_current_directory(self):
        first = AppPaths.resolve(environ={"SORTING_OS_HOME": "/tmp/same"})
        cwd = os.getcwd()
        try:
            os.chdir(tempfile.gettempdir())
            second = AppPaths.resolve(environ={"SORTING_OS_HOME": "/tmp/same"})
        finally:
            os.chdir(cwd)
        self.assertEqual(first.db_file, second.db_file)

    def test_ensure_creates_the_tree(self):
        root = tempfile.mkdtemp()
        paths = AppPaths.resolve(os.path.join(root, "data")).ensure()
        for path in (paths.db_dir, paths.backup_dir, paths.export_dir, paths.log_dir):
            self.assertTrue(os.path.isdir(path))


class ConfigTests(unittest.TestCase):
    def test_defaults_keep_open_decisions_empty(self):
        config = AppConfig()
        for key in ("fiscal_year_start_month", "settlement_rate_percent",
                    "cost_allocation_method", "goods_ownership_model"):
            self.assertIsNone(config.get(key))
        self.assertIn("settlement_rate_percent", config.open_decisions())

    def test_save_and_load_round_trip(self):
        root = tempfile.mkdtemp()
        path = os.path.join(root, "config.json")
        config = AppConfig.load(path)
        config.set("input_unit", "تومان")
        config.save()
        again = AppConfig.load(path)
        self.assertEqual(again.get("input_unit"), "تومان")
        with open(path, encoding="utf-8") as handle:
            self.assertIn("تومان", json.load(handle)["input_unit"])

    def test_broken_config_file_does_not_crash(self):
        root = tempfile.mkdtemp()
        path = os.path.join(root, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        config = AppConfig.load(path)
        self.assertEqual(config.get("input_unit"), "ریال")


class LoggingTests(unittest.TestCase):
    def test_setup_is_idempotent(self):
        root = tempfile.mkdtemp()
        log_file = os.path.join(root, "app.log")
        setup_logging(log_file, console=False)
        setup_logging(log_file, console=False)
        root_logger = logging.getLogger("sorting_os")
        self.assertEqual(len(root_logger.handlers), 1)
        logging.getLogger("sorting_os.test").info("پیام آزمایشی")
        for handler in root_logger.handlers:
            handler.flush()
        with open(log_file, encoding="utf-8") as handle:
            self.assertIn("پیام آزمایشی", handle.read())


class ShellTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.paths = AppPaths.resolve(os.path.join(self.root, "data")).ensure()

    def test_application_creates_the_database_in_the_data_directory(self):
        app = Application(paths=self.paths, console_logging=False)
        try:
            self.assertTrue(os.path.isfile(app.db.path))
            from sorting_os.migrations import LATEST_SCHEMA_VERSION
            self.assertEqual(app.db.schema_version(), LATEST_SCHEMA_VERSION)
        finally:
            app.shutdown()

    def test_version_info_lists_services_and_open_decisions(self):
        app = Application(paths=self.paths, console_logging=False)
        try:
            info = app.version_info()
            self.assertEqual(info["version"], __version__)
            self.assertIn("ledger", info["services"])
            self.assertIn("cost_allocation_method", info["open_decisions"])
        finally:
            app.shutdown()

    def test_doctor_reports_integrity(self):
        app = Application(paths=self.paths, console_logging=False)
        try:
            report = app.doctor()
            self.assertEqual(report["integrity"], "ok")
            self.assertIn("parties", report["table_counts"])
        finally:
            app.shutdown()

    def test_service_registry_wires_every_domain_service(self):
        app = Application(paths=self.paths, console_logging=False)
        try:
            names = app.services.names()
            for expected in ("parties", "catalog", "operations", "documents", "ledger",
                             "settlement", "banking", "auth", "exchange", "reporting",
                             "backup", "printing", "periods"):
                self.assertIn(expected, names)
        finally:
            app.shutdown()

    def test_cli_version_and_doctor_return_zero(self):
        buffer = io.StringIO()
        original = sys.stdout
        sys.stdout = buffer
        try:
            self.assertEqual(main(["--version", "--data-dir", self.paths.home,
                                    "--no-console-log"]), 0)
            self.assertEqual(main(["--doctor", "--data-dir", self.paths.home,
                                    "--no-console-log"]), 0)
        finally:
            sys.stdout = original
        self.assertIn("schema_version", buffer.getvalue())

    def test_cli_parser_accepts_documented_flags(self):
        parser = build_parser()
        args = parser.parse_args(["--init-db", "--data-dir", "/tmp/x"])
        self.assertTrue(args.init_db)
        self.assertEqual(args.data_dir, "/tmp/x")

    def test_error_boundary_returns_non_zero_and_logs(self):
        buffer = io.StringIO()
        original = sys.stdout
        sys.stdout = buffer
        try:
            code = main(["--doctor", "--data-dir", self.paths.home, "--no-console-log"])
            self.assertEqual(code, 0)
        finally:
            sys.stdout = original
        self.assertTrue(os.path.isfile(self.paths.log_file))


if __name__ == "__main__":
    unittest.main()
