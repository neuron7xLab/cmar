"""CMAR runtime HTTP server (zero-dependency, stdlib only).

Moves CMAR from a dev-only CLI into a running service that external agents can
call over HTTP for real load. Read-only and fail-closed:

- the repository root is fixed at launch; clients cannot scan arbitrary paths;
- GitHub endpoints use the server's local `gh` auth and fail closed without it;
- tokens are never returned (the activity collector already redacts them).

Security note: binds to 127.0.0.1 by default. Exposing it on a public interface
shares the server's GitHub read scope with any caller — put it behind an
authenticating proxy before doing so.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .github_activity import collect_github_activity
from .integrator import integrate_artifact_streams
from .runtime import run_runtime_pipeline


def _make_handler(root: str):
    base = str(Path(root).resolve())

    class CMARHandler(BaseHTTPRequestHandler):
        server_version = f"CMAR/{__version__}"

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:  # keep stdout clean; never log tokens
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            route = parsed.path.rstrip("/") or "/"
            q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                if route in ("/", "/health"):
                    self._send(200, {"status": "ok", "service": "cmar", "version": __version__, "root": base})
                elif route == "/version":
                    self._send(200, {"version": __version__})
                elif route == "/runtime":
                    owner = q.get("github_owner")
                    days = int(q.get("days", 30))
                    rep = run_runtime_pipeline(base, github_owner=owner, days=days)
                    self._send(200, rep.to_dict())
                elif route == "/integrate":
                    owner = q.get("github_owner")
                    gh = collect_github_activity(owner, int(q.get("days", 30))).to_dict() if owner else None
                    self._send(200, integrate_artifact_streams(base, github_activity=gh).to_dict())
                elif route == "/github-activity":
                    owner = q.get("owner")
                    if not owner:
                        self._send(400, {"error": "missing_owner", "hint": "/github-activity?owner=<login>&days=30"})
                        return
                    rep = collect_github_activity(owner, int(q.get("days", 30)))
                    self._send(200 if rep.authenticated else 401, rep.to_dict())
                else:
                    self._send(404, {"error": "not_found", "path": route,
                                     "routes": ["/health", "/version", "/runtime", "/integrate", "/github-activity"]})
            except Exception as exc:  # fail closed with a machine-readable error
                self._send(500, {"error": "internal", "type": type(exc).__name__})

    return CMARHandler


def serve(host: str = "127.0.0.1", port: int = 8787, root: str = ".") -> ThreadingHTTPServer:
    """Create (but do not block on) a CMAR runtime server bound to host:port."""
    httpd = ThreadingHTTPServer((host, port), _make_handler(root))
    return httpd


def run(host: str = "127.0.0.1", port: int = 8787, root: str = ".") -> int:
    httpd = serve(host, port, root)
    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    print(json.dumps({"event": "cmar_serve_start", "host": bound_host, "port": bound_port,
                      "root": str(Path(root).resolve()), "version": __version__}))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
