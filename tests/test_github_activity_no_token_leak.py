from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from cmar import github_activity as ga

SECRET = "ghp_thisIsAFakeTokenThatMustNeverLeak0000"


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


class NoTokenLeakTests(unittest.TestCase):
    def test_token_never_appears_in_report_even_if_gh_leaks_it(self):
        def leaky(args):
            joined = " ".join(args)
            if args[:2] == ["auth", "status"]:
                # Even a leaky auth banner containing the token must not propagate.
                return _proc(returncode=0, stderr=f"Token: {SECRET}")
            if "users/acme" in joined and "/repos" not in joined:
                return _proc(stdout=json.dumps({"type": "Organization"}))
            if "search/" in joined:
                return _proc(stdout=json.dumps({"total_count": 0, "items": []}))
            return _proc(stdout="[]")

        with mock.patch.object(ga, "_run_gh", side_effect=leaky):
            rep = ga.collect_github_activity("acme", days=30)
        self.assertNotIn(SECRET, json.dumps(rep.to_dict()))

    def test_failed_api_error_does_not_carry_token(self):
        def leaky_error(args):
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            # gh error text that (hypothetically) embeds a token must be truncated/redacted
            return _proc(returncode=1, stderr=f"HTTP 401 Authorization: Bearer {SECRET}")

        with mock.patch.object(ga, "_run_gh", side_effect=leaky_error):
            rep = ga.collect_github_activity("acme", days=30)
        blob = json.dumps(rep.to_dict())
        self.assertNotIn(SECRET, blob)


if __name__ == "__main__":
    unittest.main()
