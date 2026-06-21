"""Tests for n7x.pipeline.normalizer"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import unittest
from n7x.models import AccountSnapshot, Confidence, Metric, RepoSnapshot
from n7x.scorers.debt import score_account
from n7x.pipeline.normalizer import normalize_from_snapshot


def _make_snap(age: int = 200, ext_pr: int = 2) -> AccountSnapshot:
    snap = AccountSnapshot(handle="t", collected_at="2026-01-01T00:00:00Z",
                           window_days=90, account_age_days=age)
    snap.global_metrics = {
        "pr_created":           Metric(100, "count", "t", Confidence.HIGH),
        "pr_merged":            Metric(90,  "count", "t", Confidence.HIGH),
        "reviews_given":        Metric(10,  "count", "t", Confidence.HIGH),
        "bus_factor":           Metric(1,   "count", "t", Confidence.HIGH),
        "external_contributors":Metric(0,   "count", "t", Confidence.HIGH),
        "ext_pr_merged":        Metric(ext_pr, "count", "t", Confidence.HIGH),
        "prs_month_0": Metric(30, "count", "t", Confidence.MEDIUM),
        "prs_month_1": Metric(35, "count", "t", Confidence.MEDIUM),
        "prs_month_2": Metric(40, "count", "t", Confidence.MEDIUM),
    }
    rs = RepoSnapshot(name="r", url="x", collected_at="2026-01-01T00:00:00Z", window_days=90)
    rs.metrics = {
        "ci_runs": Metric(50, "count", "t", Confidence.HIGH),
        "ci_success_rate": Metric(0.90, "ratio", "t", Confidence.HIGH),
        "ci_fail_rate": Metric(0.10, "ratio", "t", Confidence.HIGH),
        "verified_ratio": Metric(0.90, "ratio", "t", Confidence.HIGH),
        "bot_ratio": Metric(0.10, "ratio", "t", Confidence.HIGH),
        "commits_bot": Metric(10, "count", "t", Confidence.HIGH),
        "commits_human": Metric(90, "count", "t", Confidence.HIGH),
        "deletion_ratio": Metric(0.20, "ratio", "t", Confidence.HIGH),
        "pr_merged_count": Metric(40, "count", "t", Confidence.HIGH),
        "churn_without_tests": Metric(5, "count", "t", Confidence.HIGH),
        "revert_ratio": Metric(0.02, "ratio", "t", Confidence.MEDIUM),
        "open_issues": Metric(3, "count", "t", Confidence.HIGH),
        "stale_issues_30d": Metric(1, "count", "t", Confidence.HIGH),
        "dep_alerts_open": Metric(0, "count", "t", Confidence.HIGH),
        "has_lockfile": Metric(True, "bool", "t", Confidence.HIGH),
        "lead_time_p50_hours": Metric(2.0, "hours", "t", Confidence.HIGH),
        "lead_time_p90_hours": Metric(8.0, "hours", "t", Confidence.MEDIUM),
        "active_days": Metric(45, "days", "t", Confidence.HIGH),
        "review_comments_median": Metric(1.5, "count", "t", Confidence.MEDIUM),
        "ci_cancel_rate": Metric(0.02, "ratio", "t", Confidence.MEDIUM),
        "ci_flaky_workflows": Metric(1, "count", "t", Confidence.MEDIUM),
        "last_commit_days": Metric(1, "days", "t", Confidence.HIGH),
        "additions_median": Metric(200, "LOC", "t", Confidence.MEDIUM),
        "deletions_median": Metric(30, "LOC", "t", Confidence.MEDIUM),
    }
    snap.repos = [rs]
    score_account(snap)
    return snap


class TestNormalizer(unittest.TestCase):

    def test_output_schema(self):
        snap = _make_snap()
        n = normalize_from_snapshot(snap)
        self.assertEqual(n["schema"], "n7x/normalized_state/v1")
        self.assertIn("signals", n)
        self.assertIn("blocking_signals", n)

    def test_all_values_in_unit_interval(self):
        snap = _make_snap()
        n = normalize_from_snapshot(snap)
        for k, v in n["signals"].items():
            val = v["value"]
            self.assertGreaterEqual(val, 0.0, f"{k} below 0")
            self.assertLessEqual(val, 1.0, f"{k} above 1")

    def test_sustainability_zero_for_young_account(self):
        snap = _make_snap(age=100)
        n = normalize_from_snapshot(snap)
        self.assertEqual(n["signals"]["sustainability_norm"]["confidence"], "NONE")
        self.assertEqual(n["signals"]["sustainability_norm"]["value"], 0.0)

    def test_blocking_signals_no_ext_pr(self):
        snap = _make_snap(ext_pr=0)
        n = normalize_from_snapshot(snap)
        self.assertIn("ZERO_EXTERNAL_PR", n["blocking_signals"])

    def test_void_pressure_in_range(self):
        snap = _make_snap()
        n = normalize_from_snapshot(snap)
        vp = n["signals"]["void_pressure"]["value"]
        self.assertGreaterEqual(vp, 0.0)
        self.assertLessEqual(vp, 1.0)

    def test_release_blocking_pressure_reflects_blocking_count(self):
        snap = _make_snap(age=100, ext_pr=0)  # young + no ext PR → multiple blockers
        n = normalize_from_snapshot(snap)
        self.assertGreater(n["signals"]["release_blocking_pressure"]["value"], 0.0)
        self.assertGreater(n["blocking_count"], 0)


if __name__ == "__main__":
    unittest.main()
