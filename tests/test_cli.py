# SPDX-License-Identifier: GPL-3.0-or-later
import json
import tempfile
import unittest
from pathlib import Path
from _base import SEED
from cmar.cli import main

class TestCLI(unittest.TestCase):
    def test_all_commands_return_zero_and_write_json(self):
        for cmd in ("scan","normalize","quantize","voids","plan","protocol","ledger","integrate","falsify","doctor"):
            with tempfile.TemporaryDirectory() as d:
                out = Path(d)/"o.json"
                self.assertEqual(main([cmd, str(SEED), "--out", str(out)]), 0, cmd)
                self.assertTrue(json.loads(out.read_text()))
    def test_bad_repo_returns_2(self):
        self.assertEqual(main(["scan", "/no/such/repo"]), 2)

if __name__ == "__main__":
    unittest.main()
