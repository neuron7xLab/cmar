from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from cmar import github_activity as ga


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


class UserOwnerTests(unittest.TestCase):
    """A user account must be scoped with author:<owner>, never org:<owner>."""

    def setUp(self):
        self.queries = []

        def fake(args):
            joined = " ".join(args)
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            if "users/octocat" in joined and "/repos" not in joined:
                return _proc(stdout=json.dumps({"type": "User", "login": "octocat"}))
            if "user/repos" in joined:
                return _proc(stdout=json.dumps([
                    {"full_name": "octocat/hello", "name": "hello", "private": False, "pushed_at": "2026-06-20T10:00:00Z"},
                ]))
            if "users/octocat/repos" in joined:
                return _proc(stdout=json.dumps([
                    {"full_name": "octocat/hello", "name": "hello", "private": False, "pushed_at": "2026-06-20T10:00:00Z"},
                ]))
            if "orgs/octocat/repos" in joined:
                return _proc(returncode=1, stderr="Not Found")  # must NOT be relied on
            if "search/" in joined:
                # capture the q= value to assert scoping
                if "-f" in args:
                    for i, a in enumerate(args):
                        if a == "-f" and i + 1 < len(args) and args[i + 1].startswith("q="):
                            self.queries.append(args[i + 1][2:])
                return _proc(stdout=json.dumps({"total_count": 3, "items": [{"created_at": "2026-06-20T10:00:00Z"}]}))
            return _proc(stdout="[]")

        self.fake = fake

    def test_owner_type_is_user(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            rep = ga.collect_github_activity("octocat", days=30)
        self.assertEqual(rep.owner_type, "user")

    def test_search_uses_author_scope_not_org(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            ga.collect_github_activity("octocat", days=30)
        self.assertTrue(self.queries, "no search queries captured")
        self.assertTrue(all(q.startswith("author:octocat") for q in self.queries), self.queries)
        self.assertFalse(any("org:octocat" in q for q in self.queries), self.queries)

    def test_user_repos_collected(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            rep = ga.collect_github_activity("octocat", days=30)
        self.assertEqual(rep.repositories_seen, 1)
        self.assertEqual(rep.collection_errors, [])


if __name__ == "__main__":
    unittest.main()
