# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.quantizer import quantize
from cmar.model import STATES

class TestQuantizer(unittest.TestCase):
    def test_overall_state_is_legal(self):
        self.assertIn(quantize(SEED)["overall_state"], STATES)
    def test_seed_is_not_release(self):
        self.assertNotEqual(quantize(SEED)["overall_state"], "RELEASE")
    def test_readiness_bounded(self):
        r = quantize(SEED)["readiness_score"]
        self.assertGreaterEqual(r,0.0)
        self.assertLessEqual(r,1.0)

if __name__ == "__main__":
    unittest.main()
