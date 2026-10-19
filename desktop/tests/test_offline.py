# -*- coding: utf-8 -*-
"""Offline-first guarantees (Prompt 27).

The application must work on a machine without any network.  These tests are
executable evidence:

* the package source never references a network client;
* importing the whole package does not pull a networking module;
* a full business flow still works when socket creation is blocked.
"""
from __future__ import annotations

import ast
import os
import socket
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from support import ACTOR, ServiceTestCase  # noqa: E402

DESKTOP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_DIR = os.path.join(DESKTOP_DIR, "sorting_os")

FORBIDDEN_MODULES = {"socket", "ssl", "http", "urllib", "requests", "ftplib", "smtplib",
                      "telnetlib", "websockets", "aiohttp", "pycurl"}
FORBIDDEN_NAMES = ("telemetry", "analytics", "sentry", "mixpanel", "auto_update",
                    "autoupdate")


def _module_files():
    for dirpath, _dirnames, filenames in os.walk(PACKAGE_DIR):
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


class SourceScanTests(unittest.TestCase):
    """Static analysis: the package must not import a networking client."""

    def test_no_network_client_in_the_package(self):
        offenders = []
        for path in _module_files():
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for module in names:
                    root = module.split(".")[0]
                    if root in FORBIDDEN_MODULES:
                        offenders.append("%s: import %s" % (os.path.relpath(path, PACKAGE_DIR),
                                                            module))
        self.assertEqual(offenders, [], "استفاده از کلاینت شبکه مجاز نیست: %s" % offenders)

    def test_no_telemetry_or_auto_update(self):
        offenders = []
        for path in _module_files():
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                elif isinstance(node, ast.Attribute):
                    names = [node.attr]
                for name in names:
                    lowered = name.lower()
                    for token in FORBIDDEN_NAMES:
                        if token in lowered:
                            offenders.append("%s: %s" % (os.path.relpath(path, PACKAGE_DIR),
                                                         name))
        self.assertEqual(offenders, [])


class ImportTests(unittest.TestCase):
    def test_importing_the_package_pulls_no_networking_module(self):
        # a fresh interpreter is used so that modules imported by the test
        # runner itself cannot influence the result
        program = (
            "import sys\n"
            "import sorting_os, sorting_os.app, sorting_os.services\n"
            "forbidden = {'socket', 'ssl', 'http', 'urllib', 'requests', 'ftplib',"
            " 'smtplib', 'telnetlib'}\n"
            "print(','.join(sorted(forbidden & set(sys.modules))))\n"
        )
        result = subprocess.run([sys.executable, "-c", program], cwd=DESKTOP_DIR,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        loaded = result.stdout.strip()
        self.assertEqual(loaded, "", "ماژول شبکه بارگذاری شد: %s" % loaded)


class BlockedNetworkTests(ServiceTestCase):
    """The whole flow must work while socket creation is impossible."""

    def setUp(self):
        super().setUp()
        self._real_socket = socket.socket

        def blocked(*args, **kwargs):
            raise OSError("شبکه در این آزمون مسدود است")

        socket.socket = blocked

    def tearDown(self):
        socket.socket = self._real_socket
        super().tearDown()

    def test_full_flow_works_without_network(self):
        party_id = self.make_party("باغدار آفلاین", roles=["owner"])
        customer_id = self.make_party("مشتری آفلاین", roles=["customer"])
        shipment_id = self.operations.create_shipment(party_id, "پرتقال", 500,
                                                      received_at="2026-02-01", actor=ACTOR)
        operation_id = self.operations.create_sorting_operation(
            shipment_id, 500, [{"line_type": "output", "weight_kg": 450},
                                {"line_type": "waste", "weight_kg": 50}],
            waste_weight_kg=50, measured_at="2026-02-02", actor=ACTOR)
        self.operations.confirm_sorting_operation(operation_id, actor=ACTOR)
        invoice_id = self.documents.create_invoice(
            customer_id, document_date="2026-02-03",
            lines=[{"weight_kg": 450, "unit_price": 1000}], actor=ACTOR)
        self.documents.confirm_invoice(invoice_id, actor=ACTOR)
        self.ledger.post_invoice(invoice_id, actor=ACTOR)

        dashboard = self.reports.dashboard(as_of="2026-02-28")
        self.assertEqual(dashboard["commercial"]["confirmed_invoices"], 1)
        self.assertTrue(self.ledger.book.trial_balance()["is_balanced"])

    def test_backup_works_without_network(self):
        target = os.path.join(self.db_path + "-backups")
        report = self.backups.create(target, actor=ACTOR)
        self.assertTrue(os.path.isfile(report["path"]))


if __name__ == "__main__":
    unittest.main()
