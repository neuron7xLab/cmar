from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from cmar import github_activity as ga


def _proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr)


class OrgOwnerTests(unittest.TestCase):
    """An organization must be scoped with org:<owner>."""

    def setUp(self):
        self.queries = []

        def fake(args):
            joined = " ".join(args)
            if args[:2] == ["auth", "status"]:
                return _proc(returncode=0)
            if "users/acme" in joined and "/repos" not in joined:
                return _proc(stdout=json.dumps({"type": "Organization", "login": "acme"}))
            if "user/repos" in joined:
                return _proc(stdout=json.dumps([
                    {"full_name": "acme/svc", "name": "svc", "private": True, "pushed_at": "2026-06-21T10:00:00Z"},
                ]))
            if "orgs/acme/repos" in joined:
                return _proc(stdout=json.dumps([
                    {"full_name": "acme/svc", "name": "svc", "private": True, "pushed_at": "2026-06-21T10:00:00Z"},
                    {"full_name": "acme/site", "name": "site", "private": False, "pushed_at": "2026-06-21T10:00:00Z"},
                ]))
            if "users/acme/repos" in joined:
                return _proc(returncode=1, stderr="Not Found")
            if "search/" in joined:
                for i, a in enumerate(args):
                    if a == "-f" and i + 1 < len(args) and args[i + 1].startswith("q="):
                        self.queries.append(args[i + 1][2:])
                return _proc(stdout=json.dumps({"total_count": 5, "items": []}))
            return _proc(stdout="[]")

        self.fake = fake

    def test_owner_type_is_organization(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            rep = ga.collect_github_activity("acme", days=30)
        self.assertEqual(rep.owner_type, "organization")

    def test_search_uses_org_scope(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            ga.collect_github_activity("acme", days=30)
        self.assertTrue(self.queries)
        self.assertTrue(all(q.startswith("org:acme") for q in self.queries), self.queries)

    def test_org_repos_and_visibility(self):
        with mock.patch.object(ga, "_run_gh", side_effect=self.fake):
            rep = ga.collect_github_activity("acme", days=30)
        self.assertEqual(rep.repositories_seen, 2)
        self.assertEqual(rep.private_repositories_if_visible, 1)
        self.assertEqual(rep.collection_errors, [])


if __name__ == "__main__":
    unittest.main()
