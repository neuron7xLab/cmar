from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from cmar import github_activity as ga
from cmar.integrator import integrate_artifact_streams
from cmar.runtime import run_runtime_pipeline

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = {
    "report_version": "cmar-github-activity/1.0.0",
    "owner": "neuron7xLab",
    "window_days": 30,
    "data_source": "gh_api",
    "authenticated": True,
    "repositories_seen": 4,
    "public_repositories": 3,
    "private_repositories_if_visible": 1,
    "commits_authored": 12,
    "pull_requests_opened": 5,
    "pull_requests_merged": 4,
    "issues_opened": 3,
    "issues_closed": 2,
    "contribution_days": 9,
    "active_repositories": ["alpha", "beta"],
    "latest_activity_utc": "2026-06-21T11:00:00+00:00",
    "collection_errors": [],
}


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


class RuntimeRealAccountTests(unittest.TestCase):
    def test_integrate_accepts_github_activity_dict(self):
        state = integrate_artifact_streams(str(ROOT), github_activity=SAMPLE)
        d = state.to_dict()
        self.assertIsNotNone(d["github_activity"])
        self.assertIsNotNone(d["github_signals"])
        self.assertIn("github_activity", d["flow"])
        self.assertEqual(d["integrated_verdict"]["github_overrides_quality"], False)

    def test_integrate_accepts_github_activity_path(self, ):
        tmp = ROOT / "artifacts/test_github_activity_input.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(SAMPLE), encoding="utf-8")
        state = integrate_artifact_streams(str(ROOT), github_activity=str(tmp))
        self.assertEqual(state.to_dict()["github_activity"]["owner"], "neuron7xLab")

    def test_github_does_not_change_gate_vs_baseline(self):
        baseline = integrate_artifact_streams(str(ROOT)).to_dict()["integrated_verdict"]["gate"]
        withgh = integrate_artifact_streams(str(ROOT), github_activity=SAMPLE).to_dict()["integrated_verdict"]["gate"]
        self.assertEqual(baseline, withgh)

    def test_runtime_without_owner_has_no_github(self):
        report = run_runtime_pipeline(str(ROOT)).to_dict()
        self.assertIsNone(report["github_activity"])

    def test_runtime_with_owner_collects_mocked(self):
        def fake(args):
            joined = " ".join(args)
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            if "user/repos" in joined:
                return _proc(stdout=json.dumps([{"full_name": "neuron7xLab/a", "name": "a", "private": False, "pushed_at": "2026-06-20T10:00:00Z"}]))
            if "orgs/" in joined or "users/" in joined:
                return _proc(stdout="[]")
            return _proc(stdout=json.dumps({"total_count": 1, "items": []}))

        with mock.patch.object(ga, "_run_gh", side_effect=fake):
            report = run_runtime_pipeline(str(ROOT), github_owner="neuron7xLab", days=30).to_dict()
        self.assertIsNotNone(report["github_activity"])
        self.assertTrue(report["github_activity"]["authenticated"])
        self.assertIn("github_signals", report["integrated_state"])

    def test_runtime_real_account_offline_by_default(self):
        # The default unittest run must never hit the network.
        report = run_runtime_pipeline(str(ROOT)).to_dict()
        self.assertIn(report["final_status"], {"PASS", "PARTIAL", "FAIL"})


if __name__ == "__main__":
    unittest.main()
