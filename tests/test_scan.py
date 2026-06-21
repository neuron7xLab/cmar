# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.scan import scan_repo

class TestScan(unittest.TestCase):
    def test_scan_reports_source_and_no_tests(self):
        r = scan_repo(SEED)
        self.assertGreater(r["mass_by_category"]["source"], 0)
        self.assertFalse(r["presence"]["tests"])
        self.assertEqual(r["total_mass_bytes"], sum(r["mass_by_category"].values()))
    def test_scan_is_deterministic(self):
        self.assertEqual(scan_repo(SEED)["scan_sha256"], scan_repo(SEED)["scan_sha256"])
    def test_scan_rejects_nondir(self):
        with self.assertRaises(NotADirectoryError):
            scan_repo(SEED / "INTENT.md")

if __name__ == "__main__":
    unittest.main()
