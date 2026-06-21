"""
n7x.collectors.account — account-level data collection.
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta, timezone
from n7x import gh
from n7x.gh import BASE, InsufficientEvidence, is_bot
from n7x.models import AccountSnapshot, Confidence, Metric
from n7x.collectors import repo as repo_collector


def collect(handle: str, window: int) -> AccountSnapshot:
    now   = datetime.now(timezone.utc)
    since = (now - timedelta(days=window)).strftime("%Y-%m-%d")

    snap = AccountSnapshot(
        handle=handle,
        collected_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        window_days=window,
    )

    print(f"[account] {handle} window={window}d since={since}")

    # ── account age ──────────────────────────────────────────────────────────
    print("[1/7] Account info")
    try:
        user = gh.get(f"{BASE}/users/{handle}")
        created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
        snap.account_age_days = (now - created).days
        snap.global_metrics["account_age_days"] = Metric(
            snap.account_age_days, "days",
            f"GET /users/{handle} .created_at",
            Confidence.HIGH
        )
    except InsufficientEvidence as e:
        snap.global_metrics["account_age_days"] = Metric(
            None, "days", f"GET /users/{handle}", Confidence.NONE, str(e)
        )

    # ── global PR / review signals ────────────────────────────────────────────
    print("[2/7] Global PR signals")
    for key, q in [
        ("pr_created",   f"type:pr author:{handle} created:>={since}"),
        ("pr_merged",    f"type:pr author:{handle} is:merged merged:>={since}"),
        ("pr_unmerged",  f"type:pr author:{handle} is:closed is:unmerged closed:>={since}"),
        ("issues_opened",f"type:issue author:{handle} created:>={since}"),
        ("reviews_given",f"type:pr reviewed-by:{handle} -author:{handle} created:>={since}"),
        ("ext_pr_merged",f"type:pr author:{handle} is:merged merged:>={since} -user:{handle}"),
    ]:
        count = gh.search(q)
        snap.global_metrics[key] = Metric(
            count if count >= 0 else None,
            "count",
            f"GET /search/issues?q={q}",
            Confidence.MEDIUM if count >= 0 else Confidence.NONE,
            "search API capped at 1000" if count >= 1000 else ""
        )

    # monthly trend (3 months)
    print("[3/7] Monthly trend")
    for i in range(3):
        end_dt   = now - timedelta(days=30 * i)
        start_dt = end_dt - timedelta(days=30)
        label    = f"prs_month_{i}"
        q        = (f"type:pr author:{handle} created:"
                    f"{start_dt.strftime('%Y-%m-%d')}..{end_dt.strftime('%Y-%m-%d')}")
        count = gh.search(q)
        snap.global_metrics[label] = Metric(
            count if count >= 0 else None, "count",
            f"GET /search/issues?q={q}", Confidence.MEDIUM
        )

    # ── repos ─────────────────────────────────────────────────────────────────
    print("[4/7] Repos")
    try:
        repos_raw = gh.pages(f"{BASE}/users/{handle}/repos",
                             {"type": "public", "sort": "updated"})
        snap.global_metrics["total_public_repos"] = Metric(
            len(repos_raw), "count",
            f"GET /users/{handle}/repos?type=public",
            Confidence.HIGH
        )
        active = [
            r for r in repos_raw
            if not r.get("fork") and not r.get("archived")
            and r.get("pushed_at", "") >= since
        ]
        snap.global_metrics["active_repos"] = Metric(
            len(active), "count",
            f"filtered by pushed_at>={since}, non-fork, non-archived",
            Confidence.HIGH
        )
        print(f"  {len(active)} active repos, auditing up to 12")
        for repo in active[:12]:
            rs = repo_collector.collect(
                handle, repo["name"], repo["html_url"], since, now, window
            )
            snap.repos.append(rs)
            time.sleep(0.3)

    except InsufficientEvidence as e:
        snap.global_metrics["total_public_repos"] = Metric(
            None, "count", f"GET /users/{handle}/repos", Confidence.NONE, str(e)
        )

    # ── bus factor (top repo) ─────────────────────────────────────────────────
    print("[5/7] Bus factor")
    if snap.repos:
        top = max(
            snap.repos,
            key=lambda r: (r.metrics.get("commits_human") or Metric(0, "", "", Confidence.NONE)).value or 0
        )
        snap.global_metrics["bus_factor"] = _bus_factor(handle, top.name)

    # ── external contributors ─────────────────────────────────────────────────
    print("[6/7] External contributors")
    ext: set[str] = set()
    for rs in snap.repos[:6]:
        try:
            contribs = gh.get(f"{BASE}/repos/{handle}/{rs.name}/contributors",
                              {"per_page": 50}, allow_none=True)
            if contribs:
                for c in contribs:
                    login = c.get("login", "")
                    if login.lower() != handle.lower() and not is_bot(login):
                        ext.add(login)
        except InsufficientEvidence:
            pass
    snap.global_metrics["external_contributors"] = Metric(
        len(ext), "count",
        f"GET /repos/{handle}/*/contributors (top 6 repos)",
        Confidence.MEDIUM
    )

    print("[7/7] Done collecting")
    return snap


def _bus_factor(handle: str, repo: str) -> Metric:
    provenance = f"GET /repos/{handle}/{repo}/stats/contributors"
    try:
        data = gh.get(f"{BASE}/repos/{handle}/{repo}/stats/contributors",
                      allow_none=True)
        if not data:
            return Metric(None, "count", provenance, Confidence.NONE, "no contributor stats")
        totals: dict[str, int] = {}
        for c in data:
            login = (c.get("author") or {}).get("login", "unknown")
            if not is_bot(login):
                totals[login] = sum(w.get("c", 0) for w in c.get("weeks", []))
        grand = sum(totals.values())
        if grand == 0:
            return Metric(1, "count", provenance, Confidence.LOW)
        acc, n = 0, 0
        for v in sorted(totals.values(), reverse=True):
            acc += v
            n   += 1
            if acc >= grand * 0.5:
                break
        return Metric(n, "count", provenance, Confidence.HIGH,
                      f"smallest N covering 50% of {grand} commits")
    except InsufficientEvidence as e:
        return Metric(None, "count", provenance, Confidence.NONE, str(e))
