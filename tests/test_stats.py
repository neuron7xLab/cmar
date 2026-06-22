from __future__ import annotations

import unittest
from unittest import mock

from cmar import stats as S


ACTIVITY = {
    "owner_type": "user", "commits_authored": 875, "pull_requests_opened": 508,
    "pull_requests_merged": 455, "issues_opened": 35, "issues_closed": 20,
    "contribution_days": 18, "repositories_seen": 32, "active_repositories": ["a", "b"],
    "collection_errors": [],
}
REPOS = [
    {"full_name": "o/a", "name": "a", "private": False, "archived": False, "pushed_at": "2026-06-20T00:00:00Z"},
    {"full_name": "o/b", "name": "b", "private": False, "archived": False, "pushed_at": "2026-06-20T00:00:00Z"},
]


def _fake_scan(full_name, errors):
    if full_name == "o/a":
        return {"scanned": True, "final_status": "FAIL", "falsify_verdict": "FALSIFIED",
                "blocking_voids": 5, "valid_mass_bytes": 1000, "gap_findings": ["missing_entrypoint"]}
    return {"scanned": True, "final_status": "PARTIAL", "falsify_verdict": "NOT_FALSIFIED",
            "blocking_voids": 0, "valid_mass_bytes": 50000, "gap_findings": []}


class StatsTests(unittest.TestCase):
    def _run(self, vulns=lambda f, e: 0):
        with mock.patch.object(S, "gh_authenticated", lambda: True), \
             mock.patch.object(S, "collect_github_activity", lambda o, d: type("R", (), {"to_dict": lambda s: dict(ACTIVITY)})()), \
             mock.patch.object(S, "_public_repos", lambda o, t, e: list(REPOS)), \
             mock.patch.object(S, "_scan_repo", _fake_scan), \
             mock.patch.object(S, "_critical_vulns", vulns):
            return S.compute_owner_stats("o", days=30, generated_utc="2026-06-22T00:00:00+00:00")

    def test_aggregation_is_real(self):
        d = self._run()
        t = d["totals"]
        self.assertEqual(t["repos_scanned"], 2)
        self.assertEqual(t["total_debt_blocking_voids"], 5)
        self.assertEqual(t["falsified_repos"], 1)
        self.assertEqual(t["total_gap_findings"], 1)
        self.assertEqual(t["total_critical_vulns"], 0)
        self.assertTrue(t["vulns_data_available"])
        self.assertEqual(d["activity"]["authored_commits"], 875)

    def test_vulns_unavailable_is_not_faked(self):
        d = self._run(vulns=lambda f, e: None)
        self.assertFalse(d["totals"]["vulns_data_available"])
        # rendered as n/a, never a fabricated number
        self.assertIn("n/a", S.render_markdown(d))

    def test_fail_closed_without_auth(self):
        with mock.patch.object(S, "gh_authenticated", lambda: False):
            d = S.compute_owner_stats("o", days=30, generated_utc="t")
        self.assertFalse(d["authenticated"])
        self.assertIn("gh_auth_missing", d["collection_errors"])
        self.assertIn("auth unavailable", S.render_markdown(d))

    def test_markdown_has_markers_payload(self):
        md = S.render_markdown(self._run())
        self.assertIn("authored commits", md)
        self.assertIn("debt (blocking voids)", md)
        self.assertIn("875", md)


if __name__ == "__main__":
    unittest.main()
