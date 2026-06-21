# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.plan import build_plan

class TestPlan(unittest.TestCase):
    def test_blocking_steps_come_first(self):
        steps = build_plan(SEED)["steps"]
        blocking_idx = [i for i,s in enumerate(steps) if s["blocking"]]
        nonblock_idx = [i for i,s in enumerate(steps) if not s["blocking"]]
        if blocking_idx and nonblock_idx:
            self.assertLess(max(blocking_idx), min(nonblock_idx))
    def test_steps_numbered(self):
        steps = build_plan(SEED)["steps"]
        self.assertEqual([s["step"] for s in steps], list(range(1, len(steps)+1)))

if __name__ == "__main__":
    unittest.main()
