# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.normalizer import normalize

class TestNormalizer(unittest.TestCase):
    def test_signals_in_unit_interval(self):
        s = normalize(SEED)["signals"]
        for k, v in s.items():
            self.assertGreaterEqual(v, 0.0, k)
            self.assertLessEqual(v, 1.0, k)
    def test_seed_has_no_ci(self):
        self.assertEqual(normalize(SEED)["signals"]["ci_presence"], 0.0)
    def test_deterministic(self):
        self.assertEqual(normalize(SEED)["normalized_sha256"], normalize(SEED)["normalized_sha256"])

if __name__ == "__main__":
    unittest.main()
