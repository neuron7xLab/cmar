"""
tests/test_pipeline.py — full offline pipeline integration test.
No API calls. Verifies all stages connect correctly.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import unittest
from n7x.models import AccountSnapshot, Confidence, Metric, RepoSnapshot
from n7x.scorers.debt import score_account
from n7x.pipeline.normalizer import normalize_from_snapshot
from n7x.pipeline.quantizer import quantize
from n7x.pipeline.falsifier import falsify_from_snapshot
from n7x.pipeline.integrator import _integrate_verdict


def _full_snap() -> AccountSnapshot:
    snap = AccountSnapshot(handle="n7x", collected_at="2026-06-21T00:00:00Z",
                           window_days=90, account_age_days=313)
    snap.global_metrics = {
        "pr_created": Metric(1242, "count", "t", Confidence.HIGH),
        "pr_merged":  Metric(1142, "count", "t", Confidence.HIGH),
        "reviews_given": Metric(20, "count", "t", Confidence.HIGH),
        "bus_factor": Metric(1, "count", "t", Confidence.HIGH),
        "external_contributors": Metric(0, "count", "t", Confidence.HIGH),
        "ext_pr_merged": Metric(0, "count", "t", Confidence.HIGH),
        "prs_month_0": Metric(337, "count", "t", Confidence.MEDIUM),
        "prs_month_1": Metric(416, "count", "t", Confidence.MEDIUM),
        "prs_month_2": Metric(489, "count", "t", Confidence.MEDIUM),
    }
    rs = RepoSnapshot(name="GeoSync", url="x", collected_at="2026-06-21T00:00:00Z", window_days=90)
    rs.metrics = {
        "ci_runs": Metric(100, "count", "t", Confidence.HIGH),
        "ci_success_rate": Metric(0.90, "ratio", "t", Confidence.HIGH),
        "ci_fail_rate": Metric(0.10, "ratio", "t", Confidence.HIGH),
        "verified_ratio": Metric(0.89, "ratio", "t", Confidence.HIGH),
        "bot_ratio": Metric(0.21, "ratio", "t", Confidence.HIGH),
        "commits_bot": Metric(21, "count", "t", Confidence.HIGH),
        "commits_human": Metric(79, "count", "t", Confidence.HIGH),
        "deletion_ratio": Metric(0.008, "ratio", "t", Confidence.HIGH),
        "pr_merged_count": Metric(703, "count", "t", Confidence.MEDIUM),
        "churn_without_tests": Metric(12, "count", "t", Confidence.MEDIUM),
        "revert_ratio": Metric(0.01, "ratio", "t", Confidence.MEDIUM),
        "open_issues": Metric(3, "count", "t", Confidence.HIGH),
        "stale_issues_30d": Metric(2, "count", "t", Confidence.HIGH),
        "dep_alerts_open": Metric(0, "count", "t", Confidence.HIGH),
        "has_lockfile": Metric(True, "bool", "t", Confidence.HIGH),
        "lead_time_p50_hours": Metric(0.47, "hours", "t", Confidence.HIGH),
        "lead_time_p90_hours": Metric(4.4, "hours", "t", Confidence.MEDIUM),
        "active_days": Metric(71, "days", "t", Confidence.HIGH),
        "review_comments_median": Metric(0.0, "count", "t", Confidence.MEDIUM),
        "ci_cancel_rate": Metric(0.05, "ratio", "t", Confidence.MEDIUM),
        "ci_flaky_workflows": Metric(2, "count", "t", Confidence.MEDIUM),
        "last_commit_days": Metric(0, "days", "t", Confidence.HIGH),
        "additions_median": Metric(250, "LOC", "t", Confidence.MEDIUM),
        "deletions_median": Metric(2, "LOC", "t", Confidence.MEDIUM),
    }
    snap.repos = [rs]
    score_account(snap)
    return snap


class TestPipelineIntegration(unittest.TestCase):

    def setUp(self):
        self.snap = _full_snap()
        self.norm  = normalize_from_snapshot(self.snap)
        self.quant = quantize(self.norm)
        self.fals  = falsify_from_snapshot(self.snap)

    def test_pipeline_runs_without_exception(self):
        # setUp already ran everything — if we're here, it passed
        self.assertIsNotNone(self.norm)
        self.assertIsNotNone(self.quant)
        self.assertIsNotNone(self.fals)

    def test_norm_output_feeds_quantizer(self):
        # quantizer must accept normalizer output
        q = quantize(self.norm)
        self.assertIn("composite", q)

    def test_integrated_verdict_produced(self):
        verdict = _integrate_verdict(self.snap, self.quant, self.fals)
        valid_verdicts = [
            "BLOCKED_BY_FALSIFICATION", "BLOCKED_VOID_STATE", "BLOCKED_TERMINAL_DEBT",
            "CONDITIONAL_WEAK", "CONDITIONAL_PARTIAL", "CANDIDATE", "RELEASE_READY",
        ]
        self.assertIn(verdict, valid_verdicts)

    def test_real_account_state_matches_known_findings(self):
        """neuron7xLab known state: young account, zero external PRs → FALSIFIED"""
        self.assertEqual(self.fals["verdict"], "FALSIFIED")
        self.assertIn("F3_ZERO_EXTERNAL_VALIDATION", self.fals["falsified_checks"])
        # F5 fires only for age < 180d; account_age=313d is above threshold
        self.assertNotIn("F5_INSUFFICIENT_LONGITUDINAL_DATA", self.fals["falsified_checks"])
        self.assertIn("F6_PURE_ACCUMULATION", self.fals["falsified_checks"])

    def test_pure_accumulation_detected_in_real_state(self):
        del_sig = next(
            (s for rs in self.snap.repos for s in rs.signals if s.name == "deletion_ratio"),
            None
        )
        self.assertIsNotNone(del_sig)
        self.assertEqual(del_sig.severity, "CRITICAL")

    def test_quantized_state_capped_for_young_account(self):
        state = self.quant["composite"]["state"]
        self.assertNotIn(state, ["RELEASE", "STRONG"],
                         f"Young account with zero ext_pr should not reach STRONG/RELEASE, got {state}")

    def test_blocking_signals_propagate_across_stages(self):
        # Blocking signals from normalizer must appear in quantizer hard_overrides or blocking list
        norm_blocking = set(self.norm["blocking_signals"])
        quant_blocking = set(self.quant["blocking_signals"])
        self.assertEqual(norm_blocking, quant_blocking)


if __name__ == "__main__":
    unittest.main()
