#!/usr/bin/env python3
"""
scripts/release_check.py
Final acceptance gate — all checks must pass for RELEASE_CHECK: PASS.
Run without GH_TOKEN for offline/CI pre-check.
"""
from __future__ import annotations
import ast
import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

REQUIRED_MODULES = [
    "n7x.models",
    "n7x.gh",
    "n7x.storage",
    "n7x.collectors.repo",
    "n7x.collectors.account",
    "n7x.scorers.debt",
    "n7x.pipeline.normalizer",
    "n7x.pipeline.quantizer",
    "n7x.pipeline.falsifier",
    "n7x.pipeline.integrator",
    "n7x.renderers.readme",
    "n7x.cli",
]

REQUIRED_FILES = [
    "src/n7x/models.py",
    "src/n7x/gh.py",
    "src/n7x/storage.py",
    "src/n7x/collectors/repo.py",
    "src/n7x/collectors/account.py",
    "src/n7x/scorers/debt.py",
    "src/n7x/pipeline/normalizer.py",
    "src/n7x/pipeline/quantizer.py",
    "src/n7x/pipeline/falsifier.py",
    "src/n7x/pipeline/integrator.py",
    "src/n7x/renderers/readme.py",
    "src/n7x/cli.py",
    "tests/test_scorer.py",
    "tests/test_normalizer.py",
    "tests/test_quantizer.py",
    "tests/test_falsifier.py",
    "tests/test_pipeline.py",
    ".github/workflows/audit.yml",
    "run.py",
    "pyproject.toml",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(name: str, passed: bool, detail: str = "") -> dict:
    status = "PASS" if passed else "FAIL"
    icon   = "✅" if passed else "❌"
    print(f"  {icon} {name}: {status}" + (f" — {detail}" if detail else ""))
    return {"name": name, "status": status, "detail": detail}


def main() -> int:
    print(f"\n{'='*60}")
    print("N7X RELEASE CHECK")
    print(f"{'='*60}\n")
    results = []

    # Gate 1: Required files exist
    print("[1/5] File presence")
    for f in REQUIRED_FILES:
        path = os.path.join(ROOT, f)
        results.append(check(f"file:{f}", os.path.exists(path)))

    # Gate 2: Syntax validation
    print("\n[2/5] Syntax validation")
    py_files = [f for f in REQUIRED_FILES if f.endswith(".py")]
    for f in py_files:
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            results.append(check(f"syntax:{f}", False, "file missing"))
            continue
        try:
            with open(path) as fh:
                ast.parse(fh.read())
            results.append(check(f"syntax:{f}", True))
        except SyntaxError as e:
            results.append(check(f"syntax:{f}", False, str(e)))

    # Gate 3: Module imports
    print("\n[3/5] Module imports")
    for mod in REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            results.append(check(f"import:{mod}", True))
        except ImportError as e:
            results.append(check(f"import:{mod}", False, str(e)))

    # Gate 4: Unit tests
    print("\n[4/5] Unit tests")
    loader = unittest.TestLoader()
    suite  = loader.discover(os.path.join(ROOT, "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    test_result = runner.run(suite)
    tests_passed = test_result.wasSuccessful()
    results.append(check(
        "unit_tests",
        tests_passed,
        f"{test_result.testsRun} run, {len(test_result.failures)} fail, {len(test_result.errors)} error"
    ))

    # Gate 5: Pipeline modules offline smoke (no API)
    print("\n[5/5] Offline smoke (no API)")
    try:
        from n7x.pipeline.normalizer import normalize_from_snapshot
        from n7x.pipeline.quantizer import quantize
        from n7x.pipeline.falsifier import falsify_from_snapshot
        from n7x.models import AccountSnapshot, Confidence, Metric, RepoSnapshot
        from n7x.scorers.debt import score_account, _debt_level, _gcei_level

        # Minimal mock snap
        snap = AccountSnapshot(
            handle="test", collected_at="2026-01-01T00:00:00Z",
            window_days=90, account_age_days=200,
        )
        snap.global_metrics = {
            "pr_created":           Metric(100, "count", "test", Confidence.HIGH),
            "pr_merged":            Metric(90,  "count", "test", Confidence.HIGH),
            "reviews_given":        Metric(15,  "count", "test", Confidence.HIGH),
            "bus_factor":           Metric(2,   "count", "test", Confidence.HIGH),
            "external_contributors":Metric(3,   "count", "test", Confidence.HIGH),
            "ext_pr_merged":        Metric(2,   "count", "test", Confidence.HIGH),
            "prs_month_0":          Metric(30,  "count", "test", Confidence.MEDIUM),
            "prs_month_1":          Metric(35,  "count", "test", Confidence.MEDIUM),
            "prs_month_2":          Metric(40,  "count", "test", Confidence.MEDIUM),
        }
        rs = RepoSnapshot(name="test_repo", url="http://x", collected_at="2026-01-01T00:00:00Z", window_days=90)
        rs.metrics = {
            "ci_runs":              Metric(50,   "count", "test", Confidence.HIGH),
            "ci_success_rate":      Metric(0.90, "ratio", "test", Confidence.HIGH),
            "ci_fail_rate":         Metric(0.10, "ratio", "test", Confidence.HIGH),
            "verified_ratio":       Metric(0.92, "ratio", "test", Confidence.HIGH),
            "bot_ratio":            Metric(0.10, "ratio", "test", Confidence.HIGH),
            "commits_bot":          Metric(10,   "count", "test", Confidence.HIGH),
            "commits_human":        Metric(90,   "count", "test", Confidence.HIGH),
            "deletion_ratio":       Metric(0.15, "ratio", "test", Confidence.HIGH),
            "pr_merged_count":      Metric(40,   "count", "test", Confidence.HIGH),
            "churn_without_tests":  Metric(5,    "count", "test", Confidence.HIGH),
            "revert_ratio":         Metric(0.02, "ratio", "test", Confidence.MEDIUM),
            "open_issues":          Metric(5,    "count", "test", Confidence.HIGH),
            "stale_issues_30d":     Metric(2,    "count", "test", Confidence.HIGH),
            "dep_alerts_open":      Metric(0,    "count", "test", Confidence.HIGH),
            "has_lockfile":         Metric(True, "bool",  "test", Confidence.HIGH),
            "lead_time_p50_hours":  Metric(2.0,  "hours", "test", Confidence.HIGH),
            "lead_time_p90_hours":  Metric(8.0,  "hours", "test", Confidence.MEDIUM),
            "active_days":          Metric(45,   "days",  "test", Confidence.HIGH),
            "review_comments_median": Metric(1.5, "count", "test", Confidence.MEDIUM),
            "ci_cancel_rate":       Metric(0.02, "ratio", "test", Confidence.MEDIUM),
            "ci_flaky_workflows":   Metric(1,    "count", "test", Confidence.MEDIUM),
            "last_commit_days":     Metric(1,    "days",  "test", Confidence.HIGH),
            "additions_median":     Metric(200,  "LOC",   "test", Confidence.MEDIUM),
            "deletions_median":     Metric(30,   "LOC",   "test", Confidence.MEDIUM),
        }
        snap.repos = [rs]
        score_account(snap)

        norm  = normalize_from_snapshot(snap)
        quant = quantize(norm)
        fals  = falsify_from_snapshot(snap)

        assert "signals" in norm,                   "normalizer missing signals"
        assert "composite" in quant,                "quantizer missing composite"
        assert "verdict" in fals,                   "falsifier missing verdict"
        assert norm["signals"]["void_pressure"]["value"] >= 0.0
        assert quant["composite"]["state"] in ["VOID","WEAK","PARTIAL","STRONG","RELEASE"]
        assert fals["verdict"] in ["FALSIFIED","NOT_FALSIFIED","PARTIAL"]

        results.append(check("pipeline_smoke", True,
            f"norm✓ quant={quant['composite']['state']} falsif={fals['verdict']}"))
    except Exception as e:
        results.append(check("pipeline_smoke", False, str(e)))

    # Final verdict
    failed = [r for r in results if r["status"] == "FAIL"]
    passed = len(results) - len(failed)
    verdict = "PASS" if not failed else "FAIL"

    print(f"\n{'='*60}")
    print(f"N7X RELEASE CHECK: {verdict}")
    print(f"  {passed}/{len(results)} checks passed")
    if failed:
        print(f"  Failed ({len(failed)}):")
        for r in failed:
            print(f"    ❌ {r['name']}: {r['detail']}")
    print(f"{'='*60}\n")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
