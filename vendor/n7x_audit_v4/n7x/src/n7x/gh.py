"""
n7x.gh — GitHub API client.
Fail-closed: every call returns data or raises InsufficientEvidence.
Rate-limit aware with exponential backoff.
"""
from __future__ import annotations
import time
import os
from typing import Any
import requests

BASE = "https://api.github.com"
BOT_SUFFIXES = ("[bot]", "dependabot", "copilot", "renovate", "github-actions", "semantic-release")


class InsufficientEvidence(Exception):
    """Raised when API data is unavailable — fail-closed."""
    pass


class RateLimitExceeded(Exception):
    pass


def _headers() -> dict:
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise InsufficientEvidence("GH_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get(url: str, params: dict | None = None, allow_none: bool = False) -> Any:
    """Single GET with retry. Raises InsufficientEvidence on persistent failure."""
    hdrs = _headers()
    for attempt in range(6):
        try:
            r = requests.get(url, headers=hdrs, params=params, timeout=30)
        except requests.RequestException as e:
            if attempt == 5:
                raise InsufficientEvidence(f"network error: {url}: {e}") from e
            time.sleep(2 ** attempt)
            continue

        remaining = int(r.headers.get("X-RateLimit-Remaining", 1))
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429):
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 30))
            wait  = max(reset - time.time(), 2)
            print(f"  [rate-limit] sleeping {wait:.0f}s (remaining={remaining})")
            time.sleep(wait)
            continue
        if r.status_code == 404:
            if allow_none:
                return None
            raise InsufficientEvidence(f"404: {url}")
        if r.status_code == 422:
            # Validation failed (e.g. search query too complex)
            raise InsufficientEvidence(f"422 validation: {url} {r.text[:200]}")
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
    raise InsufficientEvidence(f"max retries exceeded: {url}")


def pages(url: str, params: dict | None = None, max_pages: int = 5) -> list:
    """Paginated GET. Returns combined list."""
    p = dict(params or {})
    p.setdefault("per_page", 100)
    result: list = []
    for page in range(1, max_pages + 1):
        p["page"] = page
        data = get(url, p, allow_none=True)
        if not data:
            break
        result.extend(data)
        if len(data) < p["per_page"]:
            break
        time.sleep(0.15)
    return result


def search(q: str) -> int:
    """Search count — returns 0 on error (search is best-effort)."""
    try:
        d = get(f"{BASE}/search/issues", {"q": q, "per_page": 1})
        return d.get("total_count", 0)
    except InsufficientEvidence:
        return -1  # sentinel: distinguish 0 from unknown


def graphql(query: str, variables: dict | None = None) -> dict:
    token = os.environ.get("GH_TOKEN", "")
    r = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    if r.status_code != 200:
        raise InsufficientEvidence(f"graphql error: {r.status_code}")
    data = r.json()
    if "errors" in data:
        raise InsufficientEvidence(f"graphql errors: {data['errors']}")
    return data.get("data", {})


def is_bot(login: str) -> bool:
    return any(s in login.lower() for s in BOT_SUFFIXES)
