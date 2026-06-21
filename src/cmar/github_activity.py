"""Real GitHub account/repository activity runtime for CMAR.

Collects engineering-activity evidence for a GitHub owner (user or org) using the
authenticated GitHub CLI (`gh api`). It is an auxiliary evidence stream: it never
fakes private data, never prints tokens, fails closed when authentication is
missing, and accumulates partial failures into ``collection_errors`` instead of
crashing.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

REPORT_VERSION = "cmar-github-activity/1.0.0"
DATA_SOURCE = "gh_api"
_GH_TIMEOUT = 60


@dataclass
class GitHubActivityReport:
    report_version: str
    owner: str
    window_days: int
    data_source: str
    authenticated: bool
    repositories_seen: int
    public_repositories: int
    private_repositories_if_visible: int | None
    commits_authored: int
    pull_requests_opened: int
    pull_requests_merged: int
    issues_opened: int
    issues_closed: int
    contribution_days: int
    active_repositories: list[str]
    latest_activity_utc: str | None
    collection_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _empty_report(owner: str, days: int, authenticated: bool, errors: list[str]) -> GitHubActivityReport:
    return GitHubActivityReport(
        report_version=REPORT_VERSION,
        owner=owner,
        window_days=days,
        data_source=DATA_SOURCE,
        authenticated=authenticated,
        repositories_seen=0,
        public_repositories=0,
        private_repositories_if_visible=None,
        commits_authored=0,
        pull_requests_opened=0,
        pull_requests_merged=0,
        issues_opened=0,
        issues_closed=0,
        contribution_days=0,
        active_repositories=[],
        latest_activity_utc=None,
        collection_errors=errors,
    )


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a `gh` command. Never logs or returns the token; only the parsed body."""
    return subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        timeout=_GH_TIMEOUT,
        check=False,
    )


def gh_authenticated() -> bool:
    """Fail-closed authentication probe via `gh auth status`."""
    try:
        return _run_gh(["auth", "status"]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _gh_api(path: str, errors: list[str], *, params: dict[str, str] | None = None, paginate: bool = False) -> Any:
    """Call `gh api PATH`; record a redacted error and return None on failure."""
    args = ["api", path, "-H", "Accept: application/vnd.github+json"]
    if paginate:
        args.append("--paginate")
    for key, val in (params or {}).items():
        args += ["-X", "GET", "-f", f"{key}={val}"]
    try:
        proc = _run_gh(args)
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(f"gh_api_exec_failed:{path}:{type(exc).__name__}")
        return None
    if proc.returncode != 0:
        # stderr may reference the endpoint but never the token (gh redacts it).
        detail = (proc.stderr or "").strip().splitlines()
        tail = detail[-1][:160] if detail else "unknown_error"
        errors.append(f"gh_api_failed:{path}:{tail}")
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        errors.append(f"gh_api_bad_json:{path}")
        return None


def _to_utc_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _utc_date(value: str | None) -> str | None:
    iso = _to_utc_iso(value)
    return iso[:10] if iso else None


def _search_total(qualifier: str, since: str, owner: str, errors: list[str], *, search: str) -> tuple[int, list[str]]:
    """Return (total_count, observed_utc_dates) for a search/{search} query."""
    query = f"org:{owner} {qualifier}:>={since}"
    data = _gh_api(f"search/{search}", errors, params={"q": query, "per_page": "100"})
    if not isinstance(data, dict):
        return 0, []
    total = int(data.get("total_count", 0) or 0)
    dates: list[str] = []
    for item in data.get("items", []) or []:
        if search == "commits":
            stamp = (item.get("commit", {}) or {}).get("author", {}).get("date")
        else:
            stamp = item.get("created_at")
        day = _utc_date(stamp)
        if day:
            dates.append(day)
    return total, dates


def collect_github_activity(owner: str, days: int = 30) -> GitHubActivityReport:
    """Collect real GitHub activity for ``owner`` over the last ``days`` days.

    Fails closed (``authenticated=False``, ``collection_errors=['gh_auth_missing']``)
    when no authenticated `gh` session is available. Partial API failures are
    accumulated in ``collection_errors`` and the report is still returned.
    """
    if days <= 0:
        days = 30
    if not gh_authenticated():
        return _empty_report(owner, days, authenticated=False, errors=["gh_auth_missing"])

    errors: list[str] = []
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(days=days)
    since = since_dt.date().isoformat()

    # --- Repository inventory (authenticated endpoints include visible private repos) ---
    repos: dict[str, dict[str, Any]] = {}
    private_visible = False

    accessible = _gh_api("user/repos", errors, params={"per_page": "100", "affiliation": "owner,organization_member,collaborator"}, paginate=True)
    if isinstance(accessible, list):
        private_visible = True
        for repo in accessible:
            full = repo.get("full_name", "")
            if full.split("/", 1)[0].lower() == owner.lower():
                repos[full] = repo

    # Public listing to complete the picture (org first, then user fallback).
    listing = _gh_api(f"orgs/{owner}/repos", errors, params={"per_page": "100", "type": "all"}, paginate=True)
    if not isinstance(listing, list):
        # 404 for a user account; drop that error and retry the user endpoint.
        if errors and errors[-1].startswith(f"gh_api_failed:orgs/{owner}/repos"):
            errors.pop()
        listing = _gh_api(f"users/{owner}/repos", errors, params={"per_page": "100", "type": "all"}, paginate=True)
    if isinstance(listing, list):
        for repo in listing:
            full = repo.get("full_name", "")
            if full and full not in repos:
                repos[full] = repo

    dates: set[str] = set()
    latest: str | None = None
    active: list[str] = []
    public_count = 0
    private_count = 0
    for full, repo in repos.items():
        if repo.get("private"):
            private_count += 1
        else:
            public_count += 1
        pushed = _to_utc_iso(repo.get("pushed_at"))
        if pushed:
            if latest is None or pushed > latest:
                latest = pushed
            if pushed[:10] >= since:
                active.append(repo.get("name", full))
                dates.add(pushed[:10])

    # --- Activity counters via the search API ---
    commits_authored, commit_dates = _search_total("committer-date", since, owner, errors, search="commits")

    def _issue_search(extra: str, date_field: str) -> tuple[int, list[str]]:
        query = f"org:{owner} {extra} {date_field}:>={since}"
        data = _gh_api("search/issues", errors, params={"q": query, "per_page": "100"})
        if not isinstance(data, dict):
            return 0, []
        total = int(data.get("total_count", 0) or 0)
        ds = [d for d in (_utc_date(i.get("created_at")) for i in (data.get("items", []) or [])) if d]
        return total, ds

    pr_opened, dpr_o = _issue_search("type:pr", "created")
    pr_merged, dpr_m = _issue_search("type:pr", "merged")
    issues_opened, di_o = _issue_search("type:issue", "created")
    issues_closed, di_c = _issue_search("type:issue", "closed")

    for d in (*commit_dates, *dpr_o, *dpr_m, *di_o, *di_c):
        if d and d >= since:
            dates.add(d)

    active_sorted = sorted(set(active))
    return GitHubActivityReport(
        report_version=REPORT_VERSION,
        owner=owner,
        window_days=days,
        data_source=DATA_SOURCE,
        authenticated=True,
        repositories_seen=len(repos),
        public_repositories=public_count,
        private_repositories_if_visible=(private_count if private_visible else None),
        commits_authored=commits_authored,
        pull_requests_opened=pr_opened,
        pull_requests_merged=pr_merged,
        issues_opened=issues_opened,
        issues_closed=issues_closed,
        contribution_days=len(dates),
        active_repositories=active_sorted,
        latest_activity_utc=latest,
        collection_errors=errors,
    )
