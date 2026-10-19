# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from database import Database

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(os.path.join(self.tmp.name,"test.sqlite3"))
    def tearDown(self): self.tmp.cleanup()
    def party(self,name="صاحب کالا",nid="001"): return self.db.save_party({"display_name":name,"national_id":nid,"phone":"09120000000","roles":"مالک کالا"})
    def test_party_create_and_duplicate_national_id_rejected(self):
        pid=self.party()
        self.assertGreater(pid,0)
        with self.assertRaises(ValueError): self.party("شخص دوم","001")
    def test_shipment_requires_active_party_and_accepts_zero_weight(self):
        pid=self.party()
        sid=self.db.create_shipment(pid,"پرتقال",0)
        self.assertEqual(self.db.list_shipments()[0]["id"],sid)
    def test_weighing_net_and_gross_tare_validation(self):
        wid=self.db.create_weighing("ورودی",1000,250)
        self.assertGreater(wid,0)
        row=self.db.list_weighings()[0]
        self.assertEqual(row["net_weight"],750)
        with self.assertRaises(ValueError): self.db.create_weighing("ورودی",100,101)
    def test_invoice_and_dashboard_aggregate(self):
        pid=self.party()
        self.db.create_invoice(pid,"فروش","2026-10-15",120000,"تست",status="قطعی")
        counts=self.db.counts()
        self.assertEqual(counts["invoice_amount"],120000)
        self.assertEqual(counts["invoices"],1)
    def test_import_preview_never_merges_by_name(self):
        self.party("علی رضایی","001")
        preview=self.db.import_parties_preview([{"name":"علی رضایی","phone":"","national_id":""},{"name":"شخص جدید","phone":"09121111111","national_id":"002"}])
        self.assertEqual(preview[0]["action"],"review")
        self.assertEqual(preview[1]["action"],"insert")
    def test_csv_export_headers(self):
        self.party()
        rows=self.db.export_rows("parties")
        self.assertIn("display_name",rows[0])

if __name__=="__main__": unittest.main()
