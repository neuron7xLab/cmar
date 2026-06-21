"""
Deterministic unit tests for n7x scorers.
No API calls — pure math verification.
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from n7x.models import Confidence, Metric, RepoSnapshot, AccountSnapshot
from n7x.scorers import debt as scorer


def make_repo(name: str, **kwargs) -> RepoSnapshot:
    rs = RepoSnapshot(name=name, url=f"https://github.com/test/{name}",
                      collected_at="2026-06-21T00:00:00Z", window_days=90)
    defaults = {
        "deletion_ratio":        Metric(0.01, "ratio", "test", Confidence.HIGH),
        "pr_merged_count":       Metric(50,   "count", "test", Confidence.HIGH),
        "churn_without_tests":   Metric(20,   "count", "test", Confidence.HIGH),
        "ci_fail_rate":          Metric(0.20, "ratio", "test", Confidence.HIGH),
        "ci_runs":               Metric(50,   "count", "test", Confidence.HIGH),
        "verified_ratio":        Metric(0.50, "ratio", "test", Confidence.HIGH),
        "unverified_count":      Metric(25,   "count", "test", Confidence.HIGH),
        "bot_ratio":             Metric(0.25, "ratio", "test", Confidence.HIGH),
        "commits_bot":           Metric(25,   "count", "test", Confidence.HIGH),
        "revert_ratio":          Metric(0.03, "ratio", "test", Confidence.HIGH),
        "open_issues":           Metric(10,   "count", "test", Confidence.HIGH),
        "stale_issues_30d":      Metric(8,    "count", "test", Confidence.HIGH),
        "dep_alerts_open":       Metric(3,    "count", "test", Confidence.HIGH),
        "fix_to_feat_ratio":     Metric(2.5,  "ratio", "test", Confidence.LOW),
        "lead_time_p50_hours":   Metric(1.0,  "hours", "test", Confidence.HIGH),
        "commits_human":         Metric(100,  "count", "test", Confidence.HIGH),
    }
    defaults.update(kwargs)
    rs.metrics = defaults
    return rs


def test_debt_score_high_for_bad_repo():
    rs = make_repo("bad")
    signals = scorer.score_repo(rs)
    rs.signals = signals
    rs.debt_score = sum(s.debt_contribution for s in signals)
    assert rs.debt_score > 30, f"Expected debt >30, got {rs.debt_score}"


def test_debt_score_low_for_healthy_repo():
    rs = make_repo(
        "good",
        deletion_ratio=Metric(0.35, "ratio", "test", Confidence.HIGH),
        churn_without_tests=Metric(1, "count", "test", Confidence.HIGH),
        ci_fail_rate=Metric(0.02, "ratio", "test", Confidence.HIGH),
        verified_ratio=Metric(0.98, "ratio", "test", Confidence.HIGH),
        bot_ratio=Metric(0.05, "ratio", "test", Confidence.HIGH),
        revert_ratio=Metric(0.01, "ratio", "test", Confidence.HIGH),
        stale_issues_30d=Metric(1, "count", "test", Confidence.HIGH),
        dep_alerts_open=Metric(0, "count", "test", Confidence.HIGH),
    )
    signals = scorer.score_repo(rs)
    total = sum(s.debt_contribution for s in signals)
    assert total < 20, f"Expected debt <20 for healthy repo, got {total}"


def test_deletion_ratio_critical_is_high_debt():
    rs = make_repo("pure_additive",
        deletion_ratio=Metric(0.005, "ratio", "test", Confidence.HIGH))
    signals = scorer.score_repo(rs)
    del_sig = next((s for s in signals if s.name == "deletion_ratio"), None)
    assert del_sig is not None, "deletion_ratio signal missing"
    assert del_sig.severity == "CRITICAL", f"Expected CRITICAL, got {del_sig.severity}"
    assert del_sig.debt_contribution >= 20


def test_no_ci_is_critical():
    rs = make_repo("no_ci",
        ci_runs=Metric(0, "count", "test", Confidence.HIGH))
    signals = scorer.score_repo(rs)
    ci_sig = next((s for s in signals if s.name == "ci_absent"), None)
    assert ci_sig is not None, "ci_absent signal missing"
    assert ci_sig.severity == "CRITICAL"
    assert ci_sig.debt_contribution >= 18


def test_geometric_mean_zero_collapses():
    """Geometric mean: near-zero collaboration cannot be offset by high activity."""
    scores = {
        "activity": 0.9, "delivery": 0.9, "quality": 0.9,
        "collaboration": 0.001,  # near-zero
        "security": 0.9, "sustainability": 0.9, "evidence": 0.9,
    }
    result = scorer._geometric_mean(scores)
    assert result < 50, f"Geometric mean should collapse with near-zero collab, got {result}"


def test_geometric_mean_all_high():
    scores = {k: 0.85 for k in
              ["activity","delivery","quality","collaboration","security","sustainability","evidence"]}
    result = scorer._geometric_mean(scores)
    assert 70 < result < 95, f"Expected 70–95, got {result}"


def test_debt_level_thresholds():
    assert scorer._debt_level(10) == "LOW"
    assert scorer._debt_level(20) == "MODERATE"
    assert scorer._debt_level(40) == "HIGH"
    assert scorer._debt_level(60) == "CRITICAL"
    assert scorer._debt_level(80) == "TERMINAL"


def test_gcei_level_thresholds():
    assert scorer._gcei_level(20) == "NOISE"
    assert scorer._gcei_level(35) == "JUNIOR"
    assert scorer._gcei_level(50) == "JUNIOR→MID"
    assert scorer._gcei_level(65) == "MID/SENIOR"
    assert scorer._gcei_level(78) == "SENIOR"
    assert scorer._gcei_level(88) == "STAFF"
    assert scorer._gcei_level(95) == "PRINCIPAL"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(failed)
