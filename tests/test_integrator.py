# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.integrator import integrate

class TestIntegrator(unittest.TestCase):
    def test_seed_blocked(self):
        self.assertEqual(integrate(SEED)["release_verdict"], "BLOCKED")
    def test_chain_present_and_rooted(self):
        i = integrate(SEED)
        self.assertEqual(len(i["root_hash"]), 64)
        self.assertEqual(i["stream_chain"][-1]["link"], i["root_hash"])

if __name__ == "__main__":
    unittest.main()
