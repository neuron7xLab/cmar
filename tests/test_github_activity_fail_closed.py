from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from cmar import github_activity as ga

ROOT = Path(__file__).resolve().parents[1]


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


class FailClosedTests(unittest.TestCase):
    def test_missing_auth_fails_closed(self):
        with mock.patch.object(ga, "_run_gh", lambda args: _proc(returncode=1, stderr="not logged in")):
            rep = ga.collect_github_activity("neuron7xLab", days=30)
        self.assertFalse(rep.authenticated)
        self.assertIn("gh_auth_missing", rep.collection_errors)
        self.assertEqual(rep.owner_type, "unknown")
        self.assertEqual(rep.commits_authored, 0)

    def test_cli_returns_nonzero_when_unauthenticated(self):
        # The CLI must exit non-zero and still emit machine-readable JSON.
        with mock.patch.object(ga, "gh_authenticated", lambda: False):
            from cmar.cli import build_parser
            import io
            import contextlib
            args = build_parser().parse_args(["github-activity", "neuron7xLab", "--out", "/tmp/ga_failclosed.json"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = args.func(args)
        self.assertNotEqual(rc, 0)
        data = json.loads(Path("/tmp/ga_failclosed.json").read_text(encoding="utf-8"))
        self.assertFalse(data["authenticated"])
        self.assertIn("gh_auth_missing", data["collection_errors"])

    def test_subprocess_cli_exit_code(self):
        # End-to-end: forcing no auth via an empty PATH makes `gh` unavailable.
        env = {"PATH": "/nonexistent", "PYTHONPATH": str(ROOT / "src")}
        r = subprocess.run([sys.executable, "-m", "cmar.cli", "github-activity", "zzz", "--out", "/tmp/ga_e2e.json"],
                           cwd=ROOT, env=env, text=True, capture_output=True)
        self.assertNotEqual(r.returncode, 0)
        data = json.loads(Path("/tmp/ga_e2e.json").read_text(encoding="utf-8"))
        self.assertFalse(data["authenticated"])
        self.assertIn("gh_auth_missing", data["collection_errors"])


if __name__ == "__main__":
    unittest.main()
