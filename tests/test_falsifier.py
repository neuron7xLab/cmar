# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED, SeedCase
from cmar.falsifier import falsify

class TestFalsifier(SeedCase):
    def test_seed_partial_not_hard_lie(self):
        self.assertEqual(falsify(SEED)["verdict"], "PARTIAL")
    def test_catches_false_release_claim(self):
        repo = self.copy_seed()
        (repo / "RELEASE_VERDICT.md").write_text("STATUS: PASS\n", encoding="utf-8")
        r = falsify(repo)
        self.assertEqual(r["verdict"], "FALSIFIED")
        self.assertTrue(r["hard_findings"])

if __name__ == "__main__":
    unittest.main()
