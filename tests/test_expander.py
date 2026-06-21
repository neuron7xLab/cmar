from __future__ import annotations

import unittest

from cmar.expander import compute_expansion
from cmar.falsifier import falsify_payload

LEDGER = {"valid_mass_bytes": 1188, "blocking_voids": 0, "voids_detected": 0, "void_closure_rate": 1.0}
SEED_LEDGER = {"valid_mass_bytes": 119, "blocking_voids": 5, "voids_detected": 6}


class ExpanderTests(unittest.TestCase):
    def test_empty_history_converging_when_no_blocking_voids(self):
        rep = compute_expansion(LEDGER, history=[], horizon=5)
        self.assertEqual(rep["expansion_verdict"], "CONVERGING")
        self.assertEqual(rep["confidence"], "LOW")
        self.assertIsNone(rep["current"]["void_closure_rate"])

    def test_projected_states_length_equals_horizon(self):
        for h in (1, 3, 5, 9):
            rep = compute_expansion(LEDGER, history=[], horizon=h)
            self.assertEqual(len(rep["projected_states"]), h)
            self.assertEqual(rep["projected_states"][-1]["iteration"], h)

    def test_potential_mass_exceeds_current_when_velocity_positive(self):
        rep = compute_expansion(SEED_LEDGER, history=[], horizon=5)
        self.assertGreater(rep["velocity"]["valid_mass_per_iteration"], 0)
        self.assertGreater(rep["potential_mass"], rep["current"]["valid_mass_bytes"])

    def test_diverging_when_blocking_voids_trend_up(self):
        # history shows voids increasing 1 -> 3 -> 5 (current)
        history = [
            {"valid_mass_bytes": 1000, "blocking_voids": 1},
            {"valid_mass_bytes": 1000, "blocking_voids": 3},
        ]
        cur = {"valid_mass_bytes": 1000, "blocking_voids": 5, "voids_detected": 5}
        rep = compute_expansion(cur, history=history, horizon=5)
        self.assertEqual(rep["expansion_verdict"], "DIVERGING")
        self.assertLess(rep["velocity"]["voids_closed_per_iteration"], 0)

    def test_diverging_when_mass_shrinks(self):
        history = [{"valid_mass_bytes": 5000, "blocking_voids": 0}]
        cur = {"valid_mass_bytes": 3000, "blocking_voids": 0, "voids_detected": 0}
        rep = compute_expansion(cur, history=history, horizon=5)
        self.assertEqual(rep["expansion_verdict"], "DIVERGING")

    def test_entropy_estimate_in_unit_interval(self):
        for ledger in (LEDGER, SEED_LEDGER, {"valid_mass_bytes": 0, "blocking_voids": 9, "voids_detected": 9}):
            rep = compute_expansion(ledger, history=[], horizon=5)
            self.assertGreaterEqual(rep["entropy_estimate"], 0.0)
            self.assertLessEqual(rep["entropy_estimate"], 1.0)

    def test_entropy_is_deterministic_formula(self):
        rep = compute_expansion(SEED_LEDGER, history=[], horizon=5)
        self.assertAlmostEqual(rep["entropy_estimate"], 5 / (6 + 1), places=6)

    def test_measured_velocity_with_history(self):
        history = [{"valid_mass_bytes": 100, "blocking_voids": 4}]
        cur = {"valid_mass_bytes": 200, "blocking_voids": 2, "voids_detected": 4}
        rep = compute_expansion(cur, history=history, horizon=3)
        self.assertEqual(rep["confidence"], "HIGH")
        self.assertEqual(rep["velocity"]["valid_mass_per_iteration"], 100.0)
        self.assertEqual(rep["velocity"]["voids_closed_per_iteration"], 2.0)


class F11InvariantTests(unittest.TestCase):
    BASE = {
        "scan": {"missing_surface": []},
        "mass_ledger": {"status": "PASS", "blocking_voids": 0, "valid_mass_bytes": 3000, "total_bytes": 5000, "voids_detected": 0},
        "protocol_report": {"valid": True},
        "quantization_report": {"verdict": "RELEASE"},
        "integrated_verdict": {"gate": "PASS"},
    }

    def test_invariant_is_registered(self):
        r = falsify_payload({**self.BASE, "expansion": {"expansion_verdict": "CONVERGING"}})
        self.assertIn("expansion_not_diverging_on_release", r.checked_invariants)

    def test_release_while_diverging_flagged(self):
        r = falsify_payload({**self.BASE, "expansion": {"expansion_verdict": "DIVERGING"}})
        self.assertIn("release_while_diverging", [f.code for f in r.findings])

    def test_converging_release_not_flagged(self):
        r = falsify_payload({**self.BASE, "expansion": {"expansion_verdict": "CONVERGING"}})
        self.assertNotIn("release_while_diverging", [f.code for f in r.findings])


if __name__ == "__main__":
    unittest.main()
