# -*- coding: utf-8 -*-
"""Operational core: shipments, weighing, sorting, inventory, dispatch."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ConflictError, ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class ShipmentAndWeighingTests(ServiceTestCase):
    def test_shipment_requires_an_active_owner(self):
        with self.assertRaises(ValidationError):
            self.operations.create_shipment(9999, "پرتقال", 100, actor=ACTOR)

    def test_shipment_ownership_stays_undetermined_by_default(self):
        owner = self.make_party()
        shipment = self.operations.get_shipment(
            self.operations.create_shipment(owner, "پرتقال", 1000, actor=ACTOR))
        self.assertEqual(shipment["ownership_model"], "undetermined")
        self.assertEqual(shipment["current_state"], "received")

    def test_shipment_rejects_invalid_ownership_model(self):
        owner = self.make_party()
        with self.assertRaises(ValidationError):
            self.operations.create_shipment(owner, "پرتقال", 10, ownership_model="whatever",
                                           actor=ACTOR)

    def test_weighing_computes_net_and_rejects_gross_below_tare(self):
        owner = self.make_party()
        shipment_id = self.operations.create_shipment(owner, "پرتقال", 1000, actor=ACTOR)
        ticket_id = self.operations.create_weighing("ورود", 1200, 300, [shipment_id], actor=ACTOR)
        with self.db.reader() as con:
            ticket = con.execute("SELECT * FROM weighing_tickets WHERE id=?",
                                 (ticket_id,)).fetchone()
        self.assertAlmostEqual(ticket["net_weight"], 900.0, places=3)
        with self.assertRaises(ValidationError):
            self.operations.create_weighing("ورود", 100, 300, [shipment_id], actor=ACTOR)

    def test_weighing_can_reference_several_shipments(self):
        owner = self.make_party()
        first = self.operations.create_shipment(owner, "پرتقال", 100, actor=ACTOR)
        second = self.operations.create_shipment(owner, "سیب", 200, actor=ACTOR)
        ticket_id = self.operations.create_weighing("ورود", 500, 100, [first, second], actor=ACTOR)
        with self.db.reader() as con:
            links = con.execute(
                "SELECT * FROM weighing_ticket_shipments WHERE weighing_ticket_id=?",
                (ticket_id,)).fetchall()
        self.assertEqual(len(links), 2)


class SortingAndInventoryTests(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.make_party()
        self.shipment_id = self.operations.create_shipment(self.owner, "پرتقال", 1000, actor=ACTOR)

    def test_mass_balance_must_hold(self):
        with self.assertRaises(ValidationError):
            self.operations.create_sorting_operation(
                self.shipment_id, 1000,
                [{"line_type": "output", "weight_kg": 900}], waste_weight_kg=50, actor=ACTOR)

    def test_balanced_sorting_operation_is_accepted(self):
        operation_id = self.operations.create_sorting_operation(
            self.shipment_id, 1000,
            [{"line_type": "output", "weight_kg": 900},
             {"line_type": "waste", "weight_kg": 80},
             {"line_type": "loss", "weight_kg": 10},
             {"line_type": "difference", "weight_kg": 10}],
            waste_weight_kg=80, loss_weight_kg=10, difference_weight_kg=10, actor=ACTOR)
        detail = self.operations.sorting_operation_detail(operation_id)
        self.assertEqual(detail["status"], "draft")
        self.assertEqual(len(detail["lines"]), 4)

    def test_confirming_sorting_posts_inventory_movements_once(self):
        location_id = self.operations.create_location("LOC-1", "انبار مرکزی", actor=ACTOR)
        operation_id = self.operations.create_sorting_operation(
            self.shipment_id, 1000,
            [{"line_type": "output", "weight_kg": 950},
             {"line_type": "waste", "weight_kg": 50}],
            waste_weight_kg=50, actor=ACTOR)
        first = self.operations.confirm_sorting_operation(operation_id, location_id, actor=ACTOR)
        second = self.operations.confirm_sorting_operation(operation_id, location_id, actor=ACTOR)
        self.assertFalse(first["already_confirmed"])
        self.assertTrue(second["already_confirmed"])
        with self.db.reader() as con:
            movements = con.execute(
                "SELECT COUNT(*) FROM inventory_transactions WHERE source_type='sorting'").fetchone()[0]
        self.assertEqual(movements, 2)

    def test_inventory_movement_is_idempotent(self):
        created = self.operations.post_inventory_movement(
            "in", 100, "manual", "SRC-1", "line-1", "manual", actor=ACTOR)
        again = self.operations.post_inventory_movement(
            "in", 100, "manual", "SRC-1", "line-1", "manual", actor=ACTOR)
        self.assertTrue(created)
        self.assertFalse(again)
        self.assertEqual(self.operations.inventory_balance()["balance_kg"], 100.0)

    def test_inventory_balance_is_derived_from_movements(self):
        self.operations.post_inventory_movement("in", 500, "src", "A", "l1", "p", actor=ACTOR)
        self.operations.post_inventory_movement("out", 200, "src", "B", "l1", "p", actor=ACTOR)
        balance = self.operations.inventory_balance()
        self.assertEqual(balance["in_kg"], 500.0)
        self.assertEqual(balance["out_kg"], 200.0)
        self.assertEqual(balance["balance_kg"], 300.0)

    def test_reservation_cannot_be_released_twice(self):
        reservation_id = self.operations.reserve(self.shipment_id, weight_kg=100, actor=ACTOR)
        self.operations.release_reservation(reservation_id, actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.operations.release_reservation(reservation_id, actor=ACTOR)


class DispatchTests(ServiceTestCase):
    def test_dispatch_requires_lines(self):
        with self.assertRaises(ValidationError):
            self.operations.create_dispatch(lines=[], actor=ACTOR)

    def test_confirming_dispatch_consumes_stock_once(self):
        owner = self.make_party()
        shipment_id = self.operations.create_shipment(owner, "پرتقال", 1000, actor=ACTOR)
        self.operations.post_inventory_movement("in", 1000, "seed", "S1", "l1", "stock",
                                                shipment_id=shipment_id, actor=ACTOR)
        dispatch_id = self.operations.create_dispatch(
            lines=[{"shipment_id": shipment_id, "weight_kg": 400}], actor=ACTOR)
        self.operations.confirm_dispatch(dispatch_id, actor=ACTOR)
        again = self.operations.confirm_dispatch(dispatch_id, actor=ACTOR)
        self.assertTrue(again["already_confirmed"])
        self.assertEqual(self.operations.inventory_balance()["balance_kg"], 600.0)
        shipment = self.operations.get_shipment(shipment_id)
        self.assertEqual(shipment["current_state"], "dispatched")

    def test_billing_basis_must_be_known(self):
        with self.assertRaises(ValidationError):
            self.operations.create_dispatch(
                lines=[{"weight_kg": 10, "billing_basis": "guess"}], actor=ACTOR)


if __name__ == "__main__":
    unittest.main()
