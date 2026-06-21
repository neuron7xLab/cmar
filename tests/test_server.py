from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from pathlib import Path

from cmar.server import serve

ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = serve("127.0.0.1", 0, str(ROOT))  # port 0 -> ephemeral
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def test_health(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "cmar")

    def test_runtime_offline(self):
        status, body = self._get("/runtime")
        self.assertEqual(status, 200)
        self.assertIn(body["final_status"], {"PASS", "PARTIAL", "FAIL"})
        self.assertIsNone(body["github_activity"])  # no owner -> no live network

    def test_github_activity_requires_owner(self):
        try:
            self._get("/github-activity")
            self.fail("expected HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            self.assertEqual(json.loads(e.read())["error"], "missing_owner")

    def test_unknown_route_404(self):
        try:
            self._get("/nope")
            self.fail("expected HTTP 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
