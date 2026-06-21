# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from _base import SEED
from cmar.doctor import doctor

class TestDoctor(unittest.TestCase):
    def test_report_complete(self):
        d = doctor(SEED)
        for k in ("readiness_score","release_verdict","falsification_verdict","healthy"):
            self.assertIn(k, d)
    def test_deterministic(self):
        self.assertEqual(doctor(SEED)["doctor_sha256"], doctor(SEED)["doctor_sha256"])

if __name__ == "__main__":
    unittest.main()
