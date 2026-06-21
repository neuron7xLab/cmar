# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import sys
import unittest
from _base import ROOT

class TestReleaseCheck(unittest.TestCase):
    def test_release_check_passes(self):
        if os.environ.get("CMAR_IN_RELEASE_CHECK"):
            self.skipTest("avoid release_check self-recursion")
        r = subprocess.run([sys.executable, str(ROOT/"scripts"/"release_check.py")],
                           cwd=ROOT, text=True, capture_output=True)
        self.assertIn("CMAR RELEASE CHECK: PASS", r.stdout, r.stdout + r.stderr)
        self.assertEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
