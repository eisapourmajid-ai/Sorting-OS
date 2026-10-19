# -*- coding: utf-8 -*-
"""Party master data, roles, identity matching and safe merge (Prompts 07-08)."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sorting_os.core import ConflictError, ValidationError  # noqa: E402
from support import ACTOR, ServiceTestCase  # noqa: E402


class PartyServiceTests(ServiceTestCase):
    def test_create_party_assigns_code_and_roles(self):
        party_id = self.parties.create("باغدار احمدی", phone="09120000000",
                                       national_id="0012345678", roles=["owner"],
                                       actor=ACTOR)
        party = self.parties.get(party_id)
        self.assertTrue(party["code"].startswith("PTY-"))
        self.assertEqual(party["roles"], "مالک کالا")
        self.assertEqual([r["role_code"] for r in self.parties.roles(party_id)], ["owner"])

    def test_duplicate_national_id_is_rejected_not_merged(self):
        self.parties.create("حسینی", national_id="0012345678", actor=ACTOR)
        with self.assertRaises(ConflictError):
            self.parties.create("حسینی دوم", national_id="0012345678", actor=ACTOR)
        self.assertEqual(len(self.parties.search("حسینی")), 1)

    def test_name_is_required(self):
        with self.assertRaises(ValidationError):
            self.parties.create("   ", actor=ACTOR)

    def test_multiple_roles_are_allowed(self):
        party_id = self.parties.create("دو نقش", roles=["owner", "customer"], actor=ACTOR)
        codes = sorted(r["role_code"] for r in self.parties.roles(party_id))
        self.assertEqual(codes, ["customer", "owner"])

    def test_similar_names_produce_suggestions_only(self):
        first = self.parties.create("محمد رضایی", phone="09120000000", actor=ACTOR)
        second = self.parties.create("محمد رضایی ", phone="09120000001", actor=ACTOR)
        candidates = self.parties.find_candidates("محمد رضایی", phone="09120000000")
        self.assertTrue(candidates)
        # suggestions only: nothing is merged automatically, both stay active
        self.assertEqual({c["party"]["id"] for c in candidates}, {first, second})
        self.assertTrue(self.parties.get(first)["is_active"])
        self.assertTrue(self.parties.get(second)["is_active"])
        # the reason always explains why the pair is similar
        for candidate in candidates:
            self.assertTrue(candidate["reason"])

    def test_match_queue_records_decisions(self):
        first = self.parties.create("حسین رضایی", actor=ACTOR)
        second = self.parties.create("حسین رضایی", actor=ACTOR)
        self.parties.enqueue_match(second, first, 0.9, "تشابه نام", actor=ACTOR)
        queue = self.parties.review_queue()
        self.assertEqual(len(queue), 1)
        self.parties.decide_match(queue[0]["id"], "dismissed", actor=ACTOR)
        self.assertEqual(self.parties.review_queue(), [])

    def test_merge_repoints_references_and_keeps_history(self):
        owner = self.parties.create("باغدار اصلی", actor=ACTOR)
        other = self.parties.create("باغدار دوم", actor=ACTOR)
        shipment_id = self.operations.create_shipment(other, "پرتقال", 100, actor=ACTOR)
        result = self.parties.merge(other, owner, actor=ACTOR)
        self.assertGreater(result["moved_rows"], 0)
        self.assertFalse(self.parties.get(other)["is_active"])
        shipment = self.operations.get_shipment(shipment_id)
        self.assertEqual(shipment["owner_party_id"], owner)
        with self.db.reader() as con:
            log = con.execute("SELECT * FROM party_merge_log").fetchone()
            self.assertEqual(log["merged_party_id"], other)
            self.assertEqual(log["target_party_id"], owner)

    def test_merge_into_self_is_rejected(self):
        party_id = self.parties.create("خودی", actor=ACTOR)
        with self.assertRaises(ValidationError):
            self.parties.merge(party_id, party_id, actor=ACTOR)

    def test_deactivate_keeps_the_party(self):
        party_id = self.parties.create("غیرفعال", actor=ACTOR)
        self.parties.deactivate(party_id, actor=ACTOR)
        self.assertFalse(self.parties.get(party_id)["is_active"])
        self.assertEqual(self.parties.search("غیرفعال"), [])


if __name__ == "__main__":
    unittest.main()
