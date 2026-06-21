# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.ledger import build_ledger

class TestLedger(unittest.TestCase):
    def test_valid_mass_le_total(self):
        led = build_ledger(SEED)
        self.assertLessEqual(led["valid_mass_bytes"], led["total_mass_bytes"])
    def test_seed_blocked(self):
        self.assertEqual(build_ledger(SEED)["status"], "BLOCKED")
    def test_chain_links_consistent(self):
        led = build_ledger(SEED)
        prev = "0"*64
        for e in led["chain"]:
            self.assertEqual(e["prev_hash"], prev)
            prev = e["record_hash"]
        self.assertEqual(led["head_hash"], prev)

if __name__ == "__main__":
    unittest.main()
