# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.voids import build_void_graph

class TestVoids(unittest.TestCase):
    def test_seed_has_blocking_voids(self):
        g = build_void_graph(SEED)
        self.assertGreater(g["blocking_voids"], 0)
        ids = {n["id"] for n in g["nodes"]}
        self.assertIn("no_tests", ids)
        self.assertIn("no_ci", ids)
    def test_pressure_bounded(self):
        self.assertLessEqual(build_void_graph(SEED)["void_pressure"], 1.0)

if __name__ == "__main__":
    unittest.main()
