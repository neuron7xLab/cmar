# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SeedCase
from cmar.autofill import autofill

class TestAutofill(SeedCase):
    def test_autofill_improves_state(self):
        repo = self.copy_seed()
        r = autofill(repo)
        self.assertTrue(r["improved"])
        self.assertLess(r["after"]["blocking_voids"], r["before"]["blocking_voids"])
        self.assertGreater(r["after"]["valid_mass_bytes"], r["before"]["valid_mass_bytes"])
    def test_before_blocked(self):
        repo = self.copy_seed()
        self.assertEqual(autofill(repo)["before"]["ledger_status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
