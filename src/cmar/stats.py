"""Owner truth-statistics: real, daily-refreshable metrics across an owner's
public repositories — debt (blocking voids), gaps (falsification findings),
critical vulnerabilities, and authored GitHub activity.

Every number is computed in the current run (clone + CMAR scan + gh api). Nothing
is faked: unavailable data is reported as null/error, never invented.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_activity import _gh_api, _run_gh, collect_github_activity, gh_authenticated
from .runtime import run_runtime_pipeline

STATS_VERSION = "cmar/owner_stats/v1"
_CLONE_TIMEOUT = 240


def _public_repos(owner: str, owner_type: str, errors: list[str]) -> list[dict[str, Any]]:
    path = f"users/{owner}/repos" if owner_type != "organization" else f"orgs/{owner}/repos"
    data = _gh_api(path, errors, params={"per_page": "100", "type": "all"}, paginate=True)
    if not isinstance(data, list):
        return []
    return [
        {"full_name": r.get("full_name", ""), "name": r.get("name", ""),
         "private": bool(r.get("private")), "archived": bool(r.get("archived")),
         "pushed_at": r.get("pushed_at")}
        for r in data if not r.get("private") and r.get("full_name")
    ]


def _critical_vulns(full_name: str, errors: list[str]) -> int | None:
    """Open critical Dependabot alerts; None if not accessible (fail-closed)."""
    data = _gh_api(f"repos/{full_name}/dependabot/alerts", errors, params={"state": "open", "per_page": "100"}, paginate=True)
    if not isinstance(data, list):
        # drop the recorded error (no access is expected for many repos) but signal unknown
        if errors and errors[-1].startswith(f"gh_api_failed:repos/{full_name}/dependabot/alerts"):
            errors.pop()
        return None
    return sum(1 for a in data if (a.get("security_advisory", {}) or {}).get("severity") == "critical")


def _scan_repo(full_name: str, errors: list[str]) -> dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="cmar_stats_"))
    try:
        url = f"https://github.com/{full_name}.git"
        proc = subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, str(tmp)],
                              text=True, capture_output=True, timeout=_CLONE_TIMEOUT, check=False)
        if proc.returncode != 0:
            errors.append(f"clone_failed:{full_name}")
            return {"scanned": False}
        rep = run_runtime_pipeline(str(tmp)).to_dict()
        integ = rep["integrated_state"]
        ledger = integ["mass_ledger"]
        fals = integ["falsification_report"]
        return {
            "scanned": True,
            "final_status": rep["final_status"],
            "falsify_verdict": fals["verdict"],
            "blocking_voids": ledger["blocking_voids"],
            "valid_mass_bytes": ledger["valid_mass_bytes"],
            "gap_findings": [f["code"] for f in fals["findings"]],
        }
    except subprocess.TimeoutExpired:
        errors.append(f"clone_timeout:{full_name}")
        return {"scanned": False}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def compute_owner_stats(owner: str, days: int = 30, scan: bool = True, generated_utc: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    if not gh_authenticated():
        return {
            "schema": STATS_VERSION, "owner": owner, "authenticated": False,
            "collection_errors": ["gh_auth_missing"],
            "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        }

    activity = collect_github_activity(owner, days).to_dict()
    errors += activity.get("collection_errors", [])
    owner_type = activity.get("owner_type", "unknown")

    repos_out: list[dict[str, Any]] = []
    vulns_available = False
    if scan:
        for r in _public_repos(owner, owner_type, errors):
            if r.get("archived"):
                continue
            entry: dict[str, Any] = {"name": r["name"], "full_name": r["full_name"]}
            entry.update(_scan_repo(r["full_name"], errors))
            cv = _critical_vulns(r["full_name"], errors)
            if cv is not None:
                vulns_available = True
            entry["critical_vulns"] = cv
            repos_out.append(entry)

    scanned = [r for r in repos_out if r.get("scanned")]
    totals = {
        "public_repos_listed": len(repos_out),
        "repos_scanned": len(scanned),
        "total_debt_blocking_voids": sum(r.get("blocking_voids", 0) for r in scanned),
        "falsified_repos": sum(1 for r in scanned if r.get("falsify_verdict") == "FALSIFIED"),
        "total_gap_findings": sum(len(r.get("gap_findings", [])) for r in scanned),
        "total_critical_vulns": sum(r.get("critical_vulns", 0) or 0 for r in scanned),
        "vulns_data_available": vulns_available,
    }

    return {
        "schema": STATS_VERSION,
        "owner": owner,
        "owner_type": owner_type,
        "authenticated": True,
        "window_days": days,
        "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "data_source": "gh_api + local CMAR scan",
        "activity": {
            "authored_commits": activity.get("commits_authored", 0),
            "pull_requests_opened": activity.get("pull_requests_opened", 0),
            "pull_requests_merged": activity.get("pull_requests_merged", 0),
            "issues_opened": activity.get("issues_opened", 0),
            "issues_closed": activity.get("issues_closed", 0),
            "contribution_days": activity.get("contribution_days", 0),
            "repositories_seen": activity.get("repositories_seen", 0),
            "active_repositories": activity.get("active_repositories", []),
        },
        "totals": totals,
        "repos": sorted(repos_out, key=lambda x: x["name"].lower()),
        "collection_errors": sorted(set(errors)),
    }


def render_markdown(stats: dict[str, Any]) -> str:
    if not stats.get("authenticated"):
        return ("### 🛰️ CMAR Truth Stats\n\n"
                f"> ❌ GitHub auth unavailable — `{', '.join(stats.get('collection_errors', []))}` "
                f"(fail-closed, no data faked). _generated {stats.get('generated_utc')}_\n")
    a = stats["activity"]
    t = stats["totals"]
    vulns = t["total_critical_vulns"] if t["vulns_data_available"] else "n/a"
    lines = [
        "### 🛰️ CMAR Truth Stats — validated by execution, not by claim",
        "",
        f"_Owner `{stats['owner']}` ({stats['owner_type']}) · last {stats['window_days']}d · "
        f"generated {stats['generated_utc']} · source: {stats['data_source']}_",
        "",
        f"| authored commits | PRs merged/opened | issues closed/opened | contribution days | repos scanned |",
        f"|---:|---:|---:|---:|---:|",
        f"| **{a['authored_commits']}** | {a['pull_requests_merged']}/{a['pull_requests_opened']} | "
        f"{a['issues_closed']}/{a['issues_opened']} | {a['contribution_days']} | {t['repos_scanned']}/{t['public_repos_listed']} |",
        "",
        f"| 🧱 debt (blocking voids) | 🕳️ gaps (falsified repos / findings) | 🔓 critical vulns |",
        f"|---:|---:|---:|",
        f"| **{t['total_debt_blocking_voids']}** | {t['falsified_repos']} repos / {t['total_gap_findings']} findings | **{vulns}** |",
        "",
    ]
    flagged = [r for r in stats["repos"] if r.get("scanned") and
               (r.get("falsify_verdict") == "FALSIFIED" or r.get("blocking_voids", 0) > 0 or (r.get("critical_vulns") or 0) > 0)]
    if flagged:
        lines += ["<details><summary>Repos needing truth-work</summary>", "",
                  "| repo | status | falsify | debt | crit vulns |", "|---|---|---|---:|---:|"]
        for r in sorted(flagged, key=lambda x: (-x.get("blocking_voids", 0), x["name"])):
            cv = r.get("critical_vulns")
            lines.append(f"| `{r['name']}` | {r['final_status']} | {r['falsify_verdict']} | "
                         f"{r.get('blocking_voids', 0)} | {cv if cv is not None else 'n/a'} |")
        lines += ["", "</details>", ""]
    if stats.get("collection_errors"):
        lines.append(f"<sub>collection notes: {', '.join(stats['collection_errors'][:8])}</sub>")
    return "\n".join(lines) + "\n"
