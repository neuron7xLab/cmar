# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED, SeedCase
from cmar.protocol import validate_protocol

class TestProtocol(SeedCase):
    def test_seed_is_honest_valid(self):
        # incomplete but makes no false release claim -> VALID
        self.assertEqual(validate_protocol(SEED)["verdict"], "VALID")
    def test_false_release_claim_is_invalid(self):
        repo = self.copy_seed()
        (repo / "RELEASE_VERDICT.md").write_text("# Verdict: PASS\n", encoding="utf-8")
        r = validate_protocol(repo)
        self.assertEqual(r["verdict"], "INVALID")
        self.assertTrue(r["violations"])

if __name__ == "__main__":
    unittest.main()
