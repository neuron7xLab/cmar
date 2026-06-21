from __future__ import annotations

import unittest

from cmar.synthesis import synthesize_cross_stream

HIGH_ACT = {
    "commit_activity_ratio": 0.9, "pr_merge_ratio": 0.9, "active_days_ratio": 0.9,
    "repository_activity_ratio": 0.9, "github_visibility_signal": 1.0,
}
LOW_ACT = {
    "commit_activity_ratio": 0.1, "pr_merge_ratio": 0.0, "active_days_ratio": 0.1,
    "repository_activity_ratio": 0.1, "github_visibility_signal": 1.0,
}


def _state(readiness, signals):
    return {"normalized_state": {"release_readiness": readiness}, "github_signals": signals}


class SynthesisTests(unittest.TestCase):
    def test_none_without_github_stream(self):
        self.assertIsNone(synthesize_cross_stream({"normalized_state": {"release_readiness": 0.9}}))

    def test_emergent_requires_both_streams(self):
        s = synthesize_cross_stream(_state(0.9, HIGH_ACT))
        self.assertTrue(s["emergent"])
        self.assertEqual(s["inputs"], ["normalized_state.release_readiness", "github_signals"])

    def test_convergent_mature(self):
        s = synthesize_cross_stream(_state(0.8, HIGH_ACT))
        self.assertEqual(s["convergence_state"], "CONVERGENT_MATURE")
        self.assertFalse(s["activity_theater_suspected"])

    def test_activity_without_structure_flags_theater(self):
        s = synthesize_cross_stream(_state(0.1, HIGH_ACT))
        self.assertEqual(s["convergence_state"], "ACTIVITY_WITHOUT_STRUCTURE")
        self.assertTrue(s["activity_theater_suspected"])

    def test_structure_without_activity(self):
        s = synthesize_cross_stream(_state(0.9, LOW_ACT))
        self.assertEqual(s["convergence_state"], "STRUCTURE_WITHOUT_ACTIVITY")
        self.assertFalse(s["activity_theater_suspected"])

    def test_immature_both(self):
        s = synthesize_cross_stream(_state(0.1, LOW_ACT))
        self.assertEqual(s["convergence_state"], "IMMATURE_BOTH_STREAMS")

    def test_never_overrides_quality(self):
        for r in (0.0, 0.5, 1.0):
            self.assertFalse(synthesize_cross_stream(_state(r, HIGH_ACT))["overrides_quality"])

    def test_coherence_bounded_and_symmetric(self):
        s = synthesize_cross_stream(_state(0.7, HIGH_ACT))
        self.assertGreaterEqual(s["stream_coherence"], 0.0)
        self.assertLessEqual(s["stream_coherence"], 1.0)


if __name__ == "__main__":
    unittest.main()
