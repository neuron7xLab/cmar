# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SeedCase
from cmar.repair import apply_repairs

class TestRepair(SeedCase):
    def test_creates_real_files(self):
        repo = self.copy_seed()
        r = apply_repairs(repo)
        self.assertIn("tests/test_smoke.py", r["created"])
        self.assertTrue((repo / "SECURITY.md").is_file())
    def test_idempotent_second_run_creates_nothing(self):
        repo = self.copy_seed()
        apply_repairs(repo)
        again = apply_repairs(repo)
        self.assertEqual(again["created"], [])

if __name__ == "__main__":
    unittest.main()
