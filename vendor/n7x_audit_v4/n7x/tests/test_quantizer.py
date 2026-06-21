"""Tests for quantizer and falsifier"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import unittest
from n7x.pipeline.quantizer import quantize, STATES
from n7x.pipeline.falsifier import falsify_from_snapshot
from n7x.models import AccountSnapshot, Confidence, Metric, RepoSnapshot
from n7x.scorers.debt import score_account
from n7x.pipeline.normalizer import normalize_from_snapshot


def _norm(ext_pr: int = 2, age: int = 200, ci_runs: int = 50) -> dict:
    snap = AccountSnapshot(handle="t", collected_at="2026-01-01T00:00:00Z",
                           window_days=90, account_age_days=age)
    snap.global_metrics = {
        "pr_created": Metric(100, "count", "t", Confidence.HIGH),
        "pr_merged":  Metric(90,  "count", "t", Confidence.HIGH),
        "reviews_given": Metric(10, "count", "t", Confidence.HIGH),
        "bus_factor": Metric(2, "count", "t", Confidence.HIGH),
        "external_contributors": Metric(3, "count", "t", Confidence.HIGH),
        "ext_pr_merged": Metric(ext_pr, "count", "t", Confidence.HIGH),
        "prs_month_0": Metric(30, "count", "t", Confidence.MEDIUM),
        "prs_month_1": Metric(35, "count", "t", Confidence.MEDIUM),
        "prs_month_2": Metric(40, "count", "t", Confidence.MEDIUM),
    }
    rs = RepoSnapshot(name="r", url="x", collected_at="2026-01-01T00:00:00Z", window_days=90)
    rs.metrics = {
        "ci_runs": Metric(ci_runs, "count", "t", Confidence.HIGH),
        "ci_success_rate": Metric(0.90 if ci_runs > 0 else 0.0, "ratio", "t", Confidence.HIGH),
        "ci_fail_rate": Metric(0.10, "ratio", "t", Confidence.HIGH),
        "verified_ratio": Metric(0.90, "ratio", "t", Confidence.HIGH),
        "bot_ratio": Metric(0.10, "ratio", "t", Confidence.HIGH),
        "commits_bot": Metric(10, "count", "t", Confidence.HIGH),
        "commits_human": Metric(90, "count", "t", Confidence.HIGH),
        "deletion_ratio": Metric(0.20, "ratio", "t", Confidence.HIGH),
        "pr_merged_count": Metric(40, "count", "t", Confidence.HIGH),
        "churn_without_tests": Metric(3, "count", "t", Confidence.HIGH),
        "revert_ratio": Metric(0.01, "ratio", "t", Confidence.MEDIUM),
        "open_issues": Metric(2, "count", "t", Confidence.HIGH),
        "stale_issues_30d": Metric(1, "count", "t", Confidence.HIGH),
        "dep_alerts_open": Metric(0, "count", "t", Confidence.HIGH),
        "has_lockfile": Metric(True, "bool", "t", Confidence.HIGH),
        "lead_time_p50_hours": Metric(2.0, "hours", "t", Confidence.HIGH),
        "lead_time_p90_hours": Metric(8.0, "hours", "t", Confidence.MEDIUM),
        "active_days": Metric(50, "days", "t", Confidence.HIGH),
        "review_comments_median": Metric(2.0, "count", "t", Confidence.MEDIUM),
        "ci_cancel_rate": Metric(0.01, "ratio", "t", Confidence.MEDIUM),
        "ci_flaky_workflows": Metric(0, "count", "t", Confidence.MEDIUM),
        "last_commit_days": Metric(1, "days", "t", Confidence.HIGH),
        "additions_median": Metric(150, "LOC", "t", Confidence.MEDIUM),
        "deletions_median": Metric(30, "LOC", "t", Confidence.MEDIUM),
    }
    snap.repos = [rs]
    score_account(snap)
    return normalize_from_snapshot(snap)


class TestQuantizer(unittest.TestCase):

    def test_output_schema(self):
        q = quantize(_norm())
        self.assertEqual(q["schema"], "n7x/quantized_state/v1")
        self.assertIn("composite", q)
        self.assertIn("verdict", q)

    def test_state_in_valid_set(self):
        q = quantize(_norm())
        self.assertIn(q["composite"]["state"], STATES)

    def test_no_ci_forces_void(self):
        n = _norm(ci_runs=0)
        q = quantize(n)
        self.assertEqual(q["composite"]["state"], "VOID")
        self.assertTrue(any("NO_CI" in o for o in q["hard_overrides"]))

    def test_zero_ext_pr_caps_release(self):
        # Build high-quality norm but ext_pr=0
        n = _norm(ext_pr=0)
        q = quantize(n)
        self.assertNotIn(q["composite"]["state"], ["RELEASE", "STRONG"],
                         "ZERO_EXTERNAL_PR should cap at PARTIAL or below")

    def test_young_account_caps_release(self):
        n = _norm(age=100)
        q = quantize(n)
        self.assertNotIn(q["composite"]["state"], ["RELEASE", "STRONG"])

    def test_release_ready_field_consistent(self):
        q = quantize(_norm())
        expected = q["composite"]["state"] == "RELEASE"
        self.assertEqual(q["release_ready"], expected)


class TestFalsifier(unittest.TestCase):

    def _make_snap(self, ext_pr: int = 5, merge_rate: float = 0.90,
                   age: int = 300, del_ratio: float = 0.20,
                   reviews: int = 15, bus_factor: int = 2) -> AccountSnapshot:
        snap = AccountSnapshot(handle="t", collected_at="2026-01-01T00:00:00Z",
                               window_days=90, account_age_days=age)
        pr_c = 100
        pr_m = int(pr_c * merge_rate)
        snap.global_metrics = {
            "pr_created": Metric(pr_c, "count", "t", Confidence.HIGH),
            "pr_merged":  Metric(pr_m, "count", "t", Confidence.HIGH),
            "reviews_given": Metric(reviews, "count", "t", Confidence.HIGH),
            "bus_factor": Metric(bus_factor, "count", "t", Confidence.HIGH),
            "external_contributors": Metric(3, "count", "t", Confidence.HIGH),
            "ext_pr_merged": Metric(ext_pr, "count", "t", Confidence.HIGH),
            "prs_month_0": Metric(30, "count", "t", Confidence.MEDIUM),
            "prs_month_1": Metric(35, "count", "t", Confidence.MEDIUM),
            "prs_month_2": Metric(40, "count", "t", Confidence.MEDIUM),
        }
        rs = RepoSnapshot(name="r", url="x", collected_at="2026-01-01T00:00:00Z", window_days=90)
        rs.metrics = {
            "ci_runs": Metric(50, "count", "t", Confidence.HIGH),
            "ci_success_rate": Metric(0.88, "ratio", "t", Confidence.HIGH),
            "ci_fail_rate": Metric(0.12, "ratio", "t", Confidence.HIGH),
            "verified_ratio": Metric(0.88, "ratio", "t", Confidence.HIGH),
            "bot_ratio": Metric(0.10, "ratio", "t", Confidence.HIGH),
            "commits_bot": Metric(10, "count", "t", Confidence.HIGH),
            "commits_human": Metric(90, "count", "t", Confidence.HIGH),
            "deletion_ratio": Metric(del_ratio, "ratio", "t", Confidence.HIGH),
            "pr_merged_count": Metric(40, "count", "t", Confidence.HIGH),
            "churn_without_tests": Metric(3, "count", "t", Confidence.HIGH),
            "revert_ratio": Metric(0.01, "ratio", "t", Confidence.MEDIUM),
            "open_issues": Metric(2, "count", "t", Confidence.HIGH),
            "stale_issues_30d": Metric(1, "count", "t", Confidence.HIGH),
            "dep_alerts_open": Metric(0, "count", "t", Confidence.HIGH),
            "has_lockfile": Metric(True, "bool", "t", Confidence.HIGH),
            "lead_time_p50_hours": Metric(2.0, "hours", "t", Confidence.HIGH),
            "lead_time_p90_hours": Metric(8.0, "hours", "t", Confidence.MEDIUM),
            "active_days": Metric(50, "days", "t", Confidence.HIGH),
            "review_comments_median": Metric(1.5, "count", "t", Confidence.MEDIUM),
            "ci_cancel_rate": Metric(0.01, "ratio", "t", Confidence.MEDIUM),
            "ci_flaky_workflows": Metric(0, "count", "t", Confidence.MEDIUM),
            "last_commit_days": Metric(1, "days", "t", Confidence.HIGH),
            "additions_median": Metric(150, "LOC", "t", Confidence.MEDIUM),
            "deletions_median": Metric(30, "LOC", "t", Confidence.MEDIUM),
        }
        snap.repos = [rs]
        score_account(snap)
        return snap

    def test_verdict_in_valid_set(self):
        snap = self._make_snap()
        f = falsify_from_snapshot(snap)
        self.assertIn(f["verdict"], ["FALSIFIED", "NOT_FALSIFIED", "PARTIAL"])

    def test_zero_ext_pr_falsified(self):
        snap = self._make_snap(ext_pr=0)
        f = falsify_from_snapshot(snap)
        self.assertEqual(f["verdict"], "FALSIFIED")
        self.assertIn("F3_ZERO_EXTERNAL_VALIDATION", f["falsified_checks"])

    def test_young_account_falsified(self):
        snap = self._make_snap(age=100)
        f = falsify_from_snapshot(snap)
        self.assertEqual(f["verdict"], "FALSIFIED")
        self.assertIn("F5_INSUFFICIENT_LONGITUDINAL_DATA", f["falsified_checks"])

    def test_pure_accumulation_falsified(self):
        snap = self._make_snap(del_ratio=0.005)
        f = falsify_from_snapshot(snap)
        self.assertIn("F6_PURE_ACCUMULATION", f["falsified_checks"])

    def test_self_merge_loop_detected(self):
        snap = self._make_snap(merge_rate=0.99, reviews=2)
        f = falsify_from_snapshot(snap)
        f2 = next((c for c in f["checks"] if c["name"] == "F2_SELF_MERGE_LOOP"), None)
        self.assertIsNotNone(f2)
        self.assertEqual(f2["result"], "FALSIFIED")

    def test_healthy_snap_not_falsified(self):
        snap = self._make_snap(ext_pr=5, merge_rate=0.85, age=300,
                               del_ratio=0.25, reviews=20, bus_factor=2)
        f = falsify_from_snapshot(snap)
        self.assertNotEqual(f["verdict"], "FALSIFIED")

    def test_summary_totals_consistent(self):
        snap = self._make_snap()
        f = falsify_from_snapshot(snap)
        s = f["summary"]
        self.assertEqual(s["total"], len(f["checks"]))
        self.assertEqual(s["falsified"] + s["partial"] + s["insufficient"] + s["passed"], s["total"])


if __name__ == "__main__":
    unittest.main()
