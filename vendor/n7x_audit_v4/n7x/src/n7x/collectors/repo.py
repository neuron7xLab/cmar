"""
n7x.collectors.repo — per-repo data collection.
Every metric: value + provenance command + confidence.
"""
from __future__ import annotations
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from n7x import gh
from n7x.gh import BASE, InsufficientEvidence, is_bot
from n7x.models import Confidence, Metric, RepoSnapshot


def collect(handle: str, repo_name: str, url: str,
            since: str, now: datetime, window: int) -> RepoSnapshot:
    snap = RepoSnapshot(
        name=repo_name,
        url=url,
        collected_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        window_days=window,
    )
    full = f"{handle}/{repo_name}"
    print(f"    [{repo_name}]", end=" ", flush=True)

    snap.metrics.update(_ci_metrics(full, since))
    print("CI", end=" ", flush=True)

    snap.metrics.update(_commit_metrics(full, since, now))
    print("commits", end=" ", flush=True)

    snap.metrics.update(_pr_metrics(full, handle, since))
    print("PRs", end=" ", flush=True)

    snap.metrics.update(_issue_metrics(full, since, now))
    print("issues", end=" ", flush=True)

    snap.metrics.update(_dependency_metrics(full))
    print("deps", end=" ", flush=True)

    snap.metrics.update(_size_metrics(full))
    print("size ✓")

    return snap


# ── CI ────────────────────────────────────────────────────────────────────────
def _ci_metrics(full: str, since: str) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    provenance = f"GET /repos/{full}/actions/runs?branch=main&created=>={since}&per_page=100"
    try:
        data = gh.get(f"{BASE}/repos/{full}/actions/runs",
                      {"branch": "main", "per_page": 100, "created": f">={since}"})
        runs = data.get("workflow_runs", [])
        total      = len(runs)
        success    = sum(1 for r in runs if r.get("conclusion") == "success")
        failure    = sum(1 for r in runs if r.get("conclusion") == "failure")
        cancelled  = sum(1 for r in runs if r.get("conclusion") == "cancelled")
        skipped    = sum(1 for r in runs if r.get("conclusion") == "skipped")

        m["ci_runs"]        = Metric(total, "count", provenance, Confidence.HIGH)
        m["ci_success_rate"]= Metric(
            round(success / total, 4) if total else 0.0, "ratio", provenance,
            Confidence.HIGH if total >= 10 else Confidence.MEDIUM,
            f"{success}/{total} runs succeeded"
        )
        m["ci_fail_rate"]   = Metric(
            round(failure / total, 4) if total else 0.0, "ratio", provenance,
            Confidence.HIGH if total >= 10 else Confidence.MEDIUM
        )
        m["ci_cancel_rate"] = Metric(
            round(cancelled / total, 4) if total else 0.0, "ratio", provenance,
            Confidence.MEDIUM
        )
        # flaky proxy: runs that passed on retry (failure then success same workflow)
        workflow_results: dict[str, list] = {}
        for r in runs:
            wf = r.get("name", "unknown")
            workflow_results.setdefault(wf, []).append(r.get("conclusion"))
        flaky = sum(
            1 for concs in workflow_results.values()
            if "failure" in concs and "success" in concs
        )
        m["ci_flaky_workflows"] = Metric(
            flaky, "count",
            f"{provenance} (workflows with both failure and success conclusions)",
            Confidence.MEDIUM, f"{flaky} workflows show flaky pattern"
        )
    except InsufficientEvidence as e:
        m["ci_runs"] = Metric(None, "count", provenance, Confidence.NONE, str(e))
    return m


# ── COMMITS ───────────────────────────────────────────────────────────────────
def _commit_metrics(full: str, since: str, now: datetime) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    provenance = f"GET /repos/{full}/commits?since={since}T00:00:00Z (paginated, max 300)"
    try:
        commits = gh.pages(f"{BASE}/repos/{full}/commits",
                           {"since": f"{since}T00:00:00Z"}, max_pages=3)
        human, bot, verified, reverts = 0, 0, 0, 0
        last_dt: datetime | None = None

        for c in commits:
            login   = (c.get("author") or {}).get("login", "")
            message = c.get("commit", {}).get("message", "").lower()
            if is_bot(login):
                bot += 1
            else:
                human += 1
                if (c.get("commit", {}).get("verification") or {}).get("verified"):
                    verified += 1
                if message.startswith("revert"):
                    reverts += 1
            # last commit timestamp
            try:
                dt = datetime.fromisoformat(
                    c["commit"]["committer"]["date"].replace("Z", "+00:00")
                )
                if last_dt is None or dt > last_dt:
                    last_dt = dt
            except Exception:
                pass

        total = human + bot
        m["commits_human"]      = Metric(human, "count", provenance, Confidence.HIGH)
        m["commits_bot"]        = Metric(bot, "count", provenance, Confidence.HIGH)
        m["bot_ratio"]          = Metric(
            round(bot / total, 4) if total else 0.0, "ratio", provenance,
            Confidence.HIGH, f"{bot}/{total} commits are bots"
        )
        m["verified_ratio"]     = Metric(
            round(verified / human, 4) if human else 0.0, "ratio", provenance,
            Confidence.HIGH if human >= 20 else Confidence.MEDIUM
        )
        # unverified_count DROPPED — derivable as (1-verified_ratio)*commits_human, redundant
        m["revert_ratio"]       = Metric(
            round(reverts / human, 4) if human else 0.0, "ratio", provenance,
            Confidence.MEDIUM, f"{reverts} revert commits"
        )
        # fix_to_feat_ratio DROPPED — conventional-commit heuristic, LOW confidence, not actionable
        m["last_commit_days"]   = Metric(
            (now - last_dt).days if last_dt else None, "days", provenance,
            Confidence.HIGH if last_dt else Confidence.NONE
        )
        # commit cadence: active days
        active_dates = set()
        for c in commits:
            try:
                dt = datetime.fromisoformat(
                    c["commit"]["committer"]["date"].replace("Z", "+00:00")
                )
                active_dates.add(dt.date())
            except Exception:
                pass
        m["active_days"]        = Metric(
            len(active_dates), "days", provenance, Confidence.HIGH
        )

    except InsufficientEvidence as e:
        m["commits_human"] = Metric(None, "count", provenance, Confidence.NONE, str(e))
    return m


# ── PR METRICS ────────────────────────────────────────────────────────────────
def _pr_metrics(full: str, handle: str, since: str) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    provenance = f"GET /repos/{full}/pulls?state=closed&sort=updated (paginated, max 200)"
    try:
        prs = gh.pages(f"{BASE}/repos/{full}/pulls",
                       {"state": "closed", "sort": "updated", "direction": "desc"},
                       max_pages=2)
        merged = [p for p in prs if p.get("merged_at")]

        additions_all, deletions_all = [], []
        lead_times: list[float] = []
        churn_no_test = 0
        large_prs = 0
        review_counts: list[int] = []

        for p in merged[:100]:
            adds = p.get("additions", 0)
            dels = p.get("deletions", 0)
            additions_all.append(adds)
            deletions_all.append(dels)

            # lead time
            try:
                created  = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
                merged_at = datetime.fromisoformat(p["merged_at"].replace("Z", "+00:00"))
                lead_times.append((merged_at - created).total_seconds() / 3600)
            except Exception:
                pass

            # churn without tests (sample large PRs)
            if adds > 100:
                large_prs += 1
                try:
                    files = gh.get(f"{BASE}/repos/{full}/pulls/{p['number']}/files",
                                   {"per_page": 30}, allow_none=True)
                    has_test = any(
                        "test" in (f.get("filename", "").lower()) or
                        f.get("filename", "").endswith(("_test.py", "spec.py", "test.ts"))
                        for f in (files or [])
                    )
                    if not has_test:
                        churn_no_test += 1
                except InsufficientEvidence:
                    pass
                time.sleep(0.05)

            # review count
            review_counts.append(p.get("review_comments", 0))

        total_add = sum(additions_all)
        total_del = sum(deletions_all)

        def _median(lst: list[float]) -> float:
            if not lst:
                return 0.0
            s = sorted(lst)
            mid = len(s) // 2
            return s[mid]

        def _percentile(lst: list[float], p: int) -> float:
            if not lst:
                return 0.0
            s = sorted(lst)
            idx = max(0, int(len(s) * p / 100) - 1)
            return s[idx]

        m["pr_merged_count"]       = Metric(len(merged), "count", provenance, Confidence.MEDIUM)
        m["deletion_ratio"]        = Metric(
            round(total_del / total_add, 4) if total_add else 0.0,
            "ratio", provenance, Confidence.MEDIUM,
            f"total: +{total_add} -{total_del} LOC across {len(merged)} PRs"
        )
        m["churn_without_tests"]   = Metric(
            churn_no_test, "count",
            f"{provenance} + GET /pulls/N/files for PRs >100 LOC",
            Confidence.MEDIUM if large_prs > 0 else Confidence.LOW,
            f"{churn_no_test}/{large_prs} large PRs had no test file touched"
        )
        m["lead_time_p50_hours"]   = Metric(
            round(_median(lead_times), 2), "hours", provenance,
            Confidence.HIGH if len(lead_times) >= 10 else Confidence.MEDIUM
        )
        m["lead_time_p90_hours"]   = Metric(
            round(_percentile(lead_times, 90), 2), "hours", provenance,
            Confidence.MEDIUM
        )
        m["additions_median"]      = Metric(
            round(_median(additions_all), 0), "LOC", provenance, Confidence.MEDIUM
        )
        m["deletions_median"]      = Metric(
            round(_median(deletions_all), 0), "LOC", provenance, Confidence.MEDIUM
        )
        m["review_comments_median"]= Metric(
            round(_median([float(x) for x in review_counts]), 1), "comments",
            provenance, Confidence.MEDIUM,
            "0 = no review discussion on most PRs"
        )

    except InsufficientEvidence as e:
        m["pr_merged_count"] = Metric(None, "count", provenance, Confidence.NONE, str(e))
    return m


# ── ISSUES ────────────────────────────────────────────────────────────────────
def _issue_metrics(full: str, since: str, now: datetime) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    provenance_open  = f"GET /repos/{full}/issues?state=open"
    provenance_close = f"GET /repos/{full}/issues?state=closed&since={since}"
    try:
        open_issues = gh.pages(f"{BASE}/repos/{full}/issues",
                               {"state": "open", "per_page": 100}, max_pages=2)
        # exclude PRs from issues endpoint
        open_issues = [i for i in open_issues if "pull_request" not in i]

        stale_threshold = (now - timedelta(days=30))
        stale = 0
        old_30 = 0
        for i in open_issues:
            try:
                created = datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
                if created < stale_threshold:
                    stale += 1
                if (now - created).days > 30:
                    old_30 += 1
            except Exception:
                pass

        closed = gh.pages(f"{BASE}/repos/{full}/issues",
                          {"state": "closed", "since": f"{since}T00:00:00Z",
                           "per_page": 100}, max_pages=2)
        closed = [i for i in closed if "pull_request" not in i]

        total_open = len(open_issues)
        total_closed = len(closed)
        close_ratio = total_closed / (total_open + total_closed) if (total_open + total_closed) else 0.0

        m["open_issues"]       = Metric(total_open, "count", provenance_open, Confidence.HIGH)
        m["stale_issues_30d"]  = Metric(stale, "count", provenance_open,
                                        Confidence.HIGH, f"{stale}/{total_open} open >30d")
        m["issue_close_ratio"] = Metric(
            round(close_ratio, 4), "ratio", provenance_close,
            Confidence.MEDIUM, f"{total_closed} closed / {total_open} open in window"
        )

    except InsufficientEvidence as e:
        m["open_issues"] = Metric(None, "count", provenance_open, Confidence.NONE, str(e))
    return m


# ── DEPENDENCY STALENESS ──────────────────────────────────────────────────────
def _dependency_metrics(full: str) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    # Try dependabot alerts (requires push scope — graceful fallback)
    provenance = f"GET /repos/{full}/dependabot/alerts?state=open"
    try:
        alerts = gh.get(f"{BASE}/repos/{full}/dependabot/alerts",
                        {"state": "open", "per_page": 30}, allow_none=True)
        if alerts is None:
            m["dep_alerts_open"] = Metric(
                None, "count", provenance, Confidence.NONE,
                "dependabot alerts not accessible (needs push scope or feature disabled)"
            )
        else:
            critical = sum(1 for a in alerts if a.get("security_advisory", {}).get("severity") == "critical")
            high     = sum(1 for a in alerts if a.get("security_advisory", {}).get("severity") == "high")
            m["dep_alerts_open"]     = Metric(len(alerts), "count", provenance, Confidence.HIGH)
            m["dep_alerts_critical"] = Metric(critical, "count", provenance, Confidence.HIGH)
            m["dep_alerts_high"]     = Metric(high, "count", provenance, Confidence.HIGH)
    except InsufficientEvidence as e:
        m["dep_alerts_open"] = Metric(None, "count", provenance, Confidence.NONE, str(e))

    # Check for requirements/pyproject presence
    prov2 = f"GET /repos/{full}/contents/pyproject.toml + requirements*.txt"
    try:
        has_pyproject = gh.get(f"{BASE}/repos/{full}/contents/pyproject.toml",
                               allow_none=True) is not None
        has_req = gh.get(f"{BASE}/repos/{full}/contents/requirements.txt",
                         allow_none=True) is not None
        has_lockfile = (
            gh.get(f"{BASE}/repos/{full}/contents/uv.lock", allow_none=True) is not None or
            gh.get(f"{BASE}/repos/{full}/contents/poetry.lock", allow_none=True) is not None
        )
        m["has_dep_manifest"] = Metric(
            has_pyproject or has_req, "bool", prov2, Confidence.HIGH
        )
        m["has_lockfile"] = Metric(
            has_lockfile, "bool",
            f"GET /repos/{full}/contents/uv.lock + poetry.lock",
            Confidence.HIGH, "lockfile = reproducible deps"
        )
    except InsufficientEvidence:
        pass

    return m


# ── SIZE / LANGUAGE ───────────────────────────────────────────────────────────
def _size_metrics(full: str) -> dict[str, Metric]:
    m: dict[str, Metric] = {}
    provenance = f"GET /repos/{full}/languages"
    try:
        langs = gh.get(f"{BASE}/repos/{full}/languages")
        total_bytes = sum(langs.values()) if langs else 0
        primary = max(langs, key=langs.get) if langs else "unknown"  # type: ignore
        m["primary_language"] = Metric(primary, "string", provenance, Confidence.HIGH)
        m["total_bytes"]      = Metric(total_bytes, "bytes", provenance, Confidence.HIGH)
        m["language_count"]   = Metric(len(langs), "count", provenance, Confidence.HIGH)
    except InsufficientEvidence as e:
        m["primary_language"] = Metric(None, "string", provenance, Confidence.NONE, str(e))
    return m
