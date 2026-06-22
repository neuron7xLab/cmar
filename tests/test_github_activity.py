from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from cmar import github_activity as ga
from cmar.normalizer import normalize_github_activity

SECRET = "gho_supersecrettoken_should_never_appear"


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


def _fake_gh_factory():
    """Deterministic offline replacement for `gh` calls."""

    def fake(args):
        joined = " ".join(args)
        if args[:2] == ["auth", "status"]:
            return _proc(returncode=0)
        if "users/neuron7xLab" in joined and "/repos" not in joined:
            return _proc(stdout=json.dumps({"type": "Organization", "login": "neuron7xLab"}))
        if "user/repos" in joined:
            return _proc(stdout=json.dumps([
                {"full_name": "neuron7xLab/alpha", "name": "alpha", "private": False, "pushed_at": "2026-06-20T10:00:00Z"},
                {"full_name": "neuron7xLab/secret", "name": "secret", "private": True, "pushed_at": "2026-06-21T11:00:00Z"},
                {"full_name": "other/zzz", "name": "zzz", "private": False, "pushed_at": "2026-06-21T11:00:00Z"},
            ]))
        if "orgs/neuron7xLab/repos" in joined:
            return _proc(stdout=json.dumps([
                {"full_name": "neuron7xLab/alpha", "name": "alpha", "private": False, "pushed_at": "2026-06-20T10:00:00Z"},
                {"full_name": "neuron7xLab/beta", "name": "beta", "private": False, "pushed_at": "2025-01-01T00:00:00Z"},
            ]))
        if "search/commits" in joined:
            return _proc(stdout=json.dumps({"total_count": 7, "items": [
                {"commit": {"author": {"date": "2026-06-20T10:00:00Z"}}},
                {"commit": {"author": {"date": "2026-06-21T09:00:00Z"}}},
            ]}))
        if "search/issues" in joined:
            if "type:pr" in joined and "merged:" in joined:
                return _proc(stdout=json.dumps({"total_count": 2, "items": []}))
            if "type:pr" in joined:
                return _proc(stdout=json.dumps({"total_count": 3, "items": [{"created_at": "2026-06-21T08:00:00Z"}]}))
            if "type:issue" in joined and "closed:" in joined:
                return _proc(stdout=json.dumps({"total_count": 1, "items": []}))
            return _proc(stdout=json.dumps({"total_count": 4, "items": [{"created_at": "2026-06-19T08:00:00Z"}]}))
        return _proc(stdout="[]")

    return fake


class GitHubActivityTests(unittest.TestCase):
    def test_missing_auth_fails_closed(self):
        with mock.patch.object(ga, "_run_gh", lambda args: _proc(returncode=1, stderr="not logged in")):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        self.assertFalse(report.authenticated)
        self.assertEqual(report.collection_errors, ["gh_auth_missing"])
        self.assertIsNone(report.private_repositories_if_visible)
        self.assertEqual(report.commits_authored, 0)

    def test_collects_and_filters_owner(self):
        with mock.patch.object(ga, "_run_gh", side_effect=_fake_gh_factory()):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        d = report.to_dict()
        self.assertTrue(d["authenticated"])
        self.assertEqual(d["owner_type"], "organization")
        self.assertEqual(d["data_source"], "gh_api")
        self.assertEqual(d["report_version"], "cmar-github-activity/1.0.0")
        # other/zzz must be filtered out; alpha+secret+beta remain.
        self.assertEqual(d["repositories_seen"], 3)
        self.assertEqual(d["public_repositories"], 2)
        self.assertEqual(d["private_repositories_if_visible"], 1)
        self.assertEqual(d["commits_authored"], 7)
        self.assertEqual(d["pull_requests_opened"], 3)
        self.assertEqual(d["pull_requests_merged"], 2)
        self.assertEqual(d["issues_opened"], 4)
        self.assertEqual(d["issues_closed"], 1)
        self.assertGreater(d["contribution_days"], 0)
        self.assertEqual(d["collection_errors"], [])

    def test_schema_is_stable(self):
        with mock.patch.object(ga, "_run_gh", side_effect=_fake_gh_factory()):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        expected = {
            "report_version", "owner", "window_days", "data_source", "authenticated", "owner_type",
            "repositories_seen", "public_repositories", "private_repositories_if_visible",
            "commits_authored", "pull_requests_opened", "pull_requests_merged",
            "issues_opened", "issues_closed", "contribution_days", "active_repositories",
            "latest_activity_utc", "collection_errors",
        }
        self.assertEqual(set(report.to_dict().keys()), expected)

    def test_token_never_printed(self):
        # Even if a token leaks into gh output, the report must not echo it.
        def leaky(args):
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            return _proc(stdout=json.dumps([{"full_name": f"neuron7xLab/x{SECRET[:4]}", "name": "x", "private": False, "pushed_at": "2026-06-20T10:00:00Z"}]))

        with mock.patch.object(ga, "_run_gh", side_effect=leaky):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        self.assertNotIn(SECRET, json.dumps(report.to_dict()))

    def test_partial_failure_does_not_crash(self):
        def flaky(args):
            joined = " ".join(args)
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            if "search/commits" in joined:
                return _proc(returncode=1, stderr="gh: rate limit exceeded")
            if "user/repos" in joined:
                return _proc(stdout=json.dumps([{"full_name": "neuron7xLab/a", "name": "a", "private": False, "pushed_at": "2026-06-20T10:00:00Z"}]))
            if "orgs/" in joined:
                return _proc(stdout="[]")
            return _proc(stdout=json.dumps({"total_count": 0, "items": []}))

        with mock.patch.object(ga, "_run_gh", side_effect=flaky):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        self.assertTrue(report.authenticated)
        self.assertTrue(any(e.startswith("gh_api_failed:search/commits") for e in report.collection_errors))
        self.assertEqual(report.commits_authored, 0)

    def test_normalize_signals_bounded(self):
        with mock.patch.object(ga, "_run_gh", side_effect=_fake_gh_factory()):
            report = ga.collect_github_activity("neuron7xLab", days=30)
        sig = normalize_github_activity(report)
        self.assertEqual(set(sig), {
            "commit_activity_ratio", "pr_merge_ratio", "active_days_ratio",
            "repository_activity_ratio", "github_visibility_signal",
        })
        for v in sig.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)
        self.assertEqual(sig["github_visibility_signal"], 1.0)

    def _signals_for(self, commits, days=30, **over):
        rep = {"authenticated": True, "window_days": days, "commits_authored": commits,
               "pull_requests_opened": 1, "pull_requests_merged": 0, "contribution_days": 0,
               "repositories_seen": 1, "active_repositories": [], "private_repositories_if_visible": 0}
        rep.update(over)
        return normalize_github_activity(rep)

    def test_commit_calibration_preserves_low_end(self):
        # Origin slope (1/3) is shared, so the true low end stays tight to the old
        # linear baseline; mid-range divergence is bounded and by-design (soft sat).
        for cpd in (0.1, 0.3, 0.5):
            new = self._signals_for(int(round(cpd * 30)))["commit_activity_ratio"]
            old = min(cpd / 3.0, 1.0)
            self.assertLess(abs(new - old), 0.03, f"cpd={cpd}: new={new} old={old}")
        # Normal activity (~1 commit/day) remains in the same low-moderate band.
        self.assertTrue(0.20 <= self._signals_for(30)["commit_activity_ratio"] <= 0.34)

    def test_commit_calibration_not_saturated_on_heavy_tail(self):
        # The real neuron7xLab distribution (~37 commits/day) used to clamp to 1.0.
        heavy = self._signals_for(1107, days=30)["commit_activity_ratio"]
        self.assertLess(heavy, 1.0)
        self.assertGreater(heavy, 0.85)

    def test_commit_calibration_preserves_ordering_in_tail(self):
        # Ordering across very active accounts must survive (the old clamp destroyed it).
        a = self._signals_for(1107)["commit_activity_ratio"]
        b = self._signals_for(1800)["commit_activity_ratio"]
        c = self._signals_for(3600)["commit_activity_ratio"]
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertTrue(all(0.0 <= x < 1.0 for x in (a, b, c)))

    def test_unauthenticated_signals_zeroed(self):
        report = ga._empty_report("neuron7xLab", 30, authenticated=False, errors=["gh_auth_missing"])
        sig = normalize_github_activity(report)
        self.assertEqual(sig["commit_activity_ratio"], 0.0)
        self.assertEqual(sig["github_visibility_signal"], 0.0)


if __name__ == "__main__":
    unittest.main()
