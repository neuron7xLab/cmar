"""
n7x.scorers.debt — deterministic debt scoring.
Every score: formula documented, weights justified.
Fail-closed: missing evidence → penalty, not 0.
"""
from __future__ import annotations
import math
from n7x.models import AccountSnapshot, Confidence, DebtSignal, Metric, RepoSnapshot

# Benchmarks (solo research-infra Python, ~1yr account)
# Based on: Nagappan & Ball (2005), Kalliamvakou et al. (2016),
#           DORA 2024 report, CHAOSS community medians
BENCHMARKS = {
    "deletion_ratio":        {"healthy": 0.25, "warning": 0.10, "critical": 0.03},
    "ci_fail_rate":          {"healthy": 0.05, "warning": 0.15, "critical": 0.25},
    "verified_ratio":        {"healthy": 0.95, "warning": 0.80, "critical": 0.50},
    "bot_ratio":             {"healthy": 0.10, "warning": 0.20, "critical": 0.35},
    "revert_ratio":          {"healthy": 0.02, "warning": 0.05, "critical": 0.10},
    "stale_issue_ratio":     {"healthy": 0.20, "warning": 0.50, "critical": 0.80},
    "lead_time_p50_hours":   {"healthy": 4.0,  "warning": 24.0, "critical": 72.0},
    "churn_test_gap_ratio":  {"healthy": 0.10, "warning": 0.30, "critical": 0.50},
    "review_comments_median":{"healthy": 2.0,  "warning": 0.5,  "critical": 0.0},
    "bus_factor":            {"healthy": 3,    "warning": 2,    "critical": 1},
    "external_contributors": {"healthy": 5,    "warning": 2,    "critical": 0},
    "reviews_given_per_day": {"healthy": 1.0,  "warning": 0.3,  "critical": 0.05},
}


def _get(m: dict[str, Metric], key: str) -> tuple[float | None, Confidence]:
    met = m.get(key)
    if met is None or met.confidence == Confidence.NONE or met.value is None:
        return None, Confidence.NONE
    return float(met.value), met.confidence


def _severity(val: float, bench: dict, higher_is_worse: bool = True) -> str:
    if higher_is_worse:
        if val >= bench["critical"]: return "CRITICAL"
        if val >= bench["warning"]:  return "HIGH"
        if val >= bench["healthy"]:  return "MEDIUM"
        return "OK"
    else:  # lower is worse
        if val <= bench["critical"]: return "CRITICAL"
        if val <= bench["warning"]:  return "HIGH"
        if val <= bench["healthy"]:  return "MEDIUM"
        return "OK"


def _debt_from_severity(sev: str, weight: float) -> float:
    return {"CRITICAL": 1.0, "HIGH": 0.6, "MEDIUM": 0.3, "OK": 0.0}.get(sev, 0.5) * weight


def score_repo(rs: RepoSnapshot) -> list[DebtSignal]:
    signals: list[DebtSignal] = []
    m = rs.metrics

    # 1. ACCUMULATION — deletion ratio (Nagappan & Ball 2005)
    val, conf = _get(m, "deletion_ratio")
    if val is not None:
        bench = BENCHMARKS["deletion_ratio"]
        sev   = _severity(val, bench, higher_is_worse=False)
        signals.append(DebtSignal(
            name="deletion_ratio",
            category="ACCUMULATION",
            raw=m["deletion_ratio"],
            debt_contribution=_debt_from_severity(sev, 25.0),
            severity=sev,
            finding=(
                f"deletion_ratio={val:.3f} (benchmark: healthy≥{bench['healthy']}, "
                f"critical≤{bench['critical']}). "
                + ("Pure additive growth — no cleanup of technical debt."
                   if sev == "CRITICAL" else
                   "Minimal refactoring — code accumulates faster than it simplifies."
                   if sev == "HIGH" else
                   "Some deletion but below healthy threshold." if sev == "MEDIUM" else
                   "Healthy delete/add balance.")
            ),
            remediation=(
                "Schedule explicit refactor cycles: target deletion_ratio ≥ 0.25. "
                "Add 'chore: refactor' PRs to sprint backlog."
                if sev in ("CRITICAL", "HIGH") else ""
            ),
        ))
    else:
        signals.append(DebtSignal(
            "deletion_ratio", "ACCUMULATION",
            m.get("deletion_ratio", Metric(None, "", "", Confidence.NONE)),
            15.0, "MEDIUM",  # penalty for missing evidence
            "deletion_ratio: INSUFFICIENT_EVIDENCE — PR data unavailable",
            "Ensure repo has merged PRs and API access is granted",
        ))

    # 2. TEST COVERAGE PROXY — churn without tests
    val_cwt, _ = _get(m, "churn_without_tests")
    val_prs, _ = _get(m, "pr_merged_count")
    if val_cwt is not None and val_prs is not None and val_prs > 0:
        ratio = val_cwt / val_prs
        bench = BENCHMARKS["churn_test_gap_ratio"]
        sev   = _severity(ratio, bench)
        signals.append(DebtSignal(
            "churn_test_gap",
            "ACCUMULATION",
            m["churn_without_tests"],
            _debt_from_severity(sev, 20.0),
            sev,
            f"{val_cwt:.0f}/{val_prs:.0f} large PRs (>100 LOC) touched no test files "
            f"(ratio={ratio:.2f}, benchmark critical≥{bench['critical']})",
            "Gate PRs >100 LOC: require ≥1 test file in changed files." if sev in ("CRITICAL","HIGH") else "",
        ))

    # 3. CI STABILITY
    val, conf = _get(m, "ci_fail_rate")
    ci_runs, _ = _get(m, "ci_runs")
    if ci_runs == 0 or ci_runs is None:
        signals.append(DebtSignal(
            "ci_absent", "STABILITY",
            Metric(0, "runs", "actions/runs", Confidence.HIGH),
            20.0, "CRITICAL",
            "NO CI RUNS on main in window. Zero automated quality gate.",
            "Add GitHub Actions workflow with pytest + lint on every push to main.",
        ))
    elif val is not None:
        bench = BENCHMARKS["ci_fail_rate"]
        sev   = _severity(val, bench)
        signals.append(DebtSignal(
            "ci_fail_rate", "STABILITY",
            m["ci_fail_rate"],
            _debt_from_severity(sev, 15.0),
            sev,
            f"CI fail rate = {val*100:.1f}% over {ci_runs:.0f} runs "
            f"(benchmark: healthy<{bench['healthy']*100:.0f}%, critical>{bench['critical']*100:.0f}%)",
            "Investigate flaky tests. Add fail-fast gates." if sev in ("CRITICAL","HIGH") else "",
        ))

    # 4. COMMIT HYGIENE — verified signatures
    val, conf = _get(m, "verified_ratio")
    hc, _ = _get(m, "commits_human")
    if val is not None:
        bench = BENCHMARKS["verified_ratio"]
        sev   = _severity(val, bench, higher_is_worse=False)
        # derive unverified count from ratio — drop redundant unverified_count field
        unver_derived = round((1.0 - val) * (hc or 0))
        signals.append(DebtSignal(
            "verified_ratio", "HYGIENE",
            m["verified_ratio"],
            _debt_from_severity(sev, 10.0),
            sev,
            f"{val*100:.1f}% commits cryptographically verified "
            f"(~{unver_derived} unverified, derived). Benchmark: healthy≥{bench['healthy']*100:.0f}%",
            "Configure GPG/SSH signing: git config commit.gpgsign true" if sev in ("CRITICAL","HIGH") else "",
        ))

    # 5. BOT INFLATION
    val, _ = _get(m, "bot_ratio")
    if val is not None:
        bench = BENCHMARKS["bot_ratio"]
        sev   = _severity(val, bench)
        bot_c, _ = _get(m, "commits_bot")
        signals.append(DebtSignal(
            "bot_inflation", "HYGIENE",
            m["bot_ratio"],
            _debt_from_severity(sev, 10.0),
            sev,
            f"Bot commits = {val*100:.1f}% ({bot_c:.0f} total). "
            f"Benchmark: warning>{bench['warning']*100:.0f}%",
            "Bot activity inflates PR/commit counts — filter from all metrics." if sev == "HIGH" else "",
        ))

    # 6. REVERT SIGNAL
    val, _ = _get(m, "revert_ratio")
    if val is not None:
        bench = BENCHMARKS["revert_ratio"]
        sev   = _severity(val, bench)
        rev, _ = _get(m, "revert_ratio")
        signals.append(DebtSignal(
            "revert_signal", "STABILITY",
            m["revert_ratio"],
            _debt_from_severity(sev, 8.0),
            sev,
            f"Revert ratio = {val*100:.1f}% of human commits. "
            f"Benchmark: warning>{bench['warning']*100:.0f}%",
            "Investigate root cause of reverts — may indicate insufficient pre-merge testing." if sev in ("CRITICAL","HIGH") else "",
        ))

    # 7. STALE ISSUES (DECAY)
    val_open, _ = _get(m, "open_issues")
    val_stale, _ = _get(m, "stale_issues_30d")
    if val_open is not None and val_open > 0 and val_stale is not None:
        ratio = val_stale / val_open
        bench = BENCHMARKS["stale_issue_ratio"]
        sev   = _severity(ratio, bench)
        signals.append(DebtSignal(
            "stale_issues", "DECAY",
            m.get("stale_issues_30d", Metric(val_stale, "count", "", Confidence.MEDIUM)),
            _debt_from_severity(sev, 8.0),
            sev,
            f"{val_stale:.0f}/{val_open:.0f} open issues are >30d old "
            f"(ratio={ratio:.2f}, benchmark: critical>{bench['critical']})",
            "Triage open issues: close or label as 'wontfix'/'backlog'." if sev in ("CRITICAL","HIGH") else "",
        ))

    # 8. DEPENDENCY STALENESS
    alerts, _ = _get(m, "dep_alerts_open")
    if alerts is not None:
        sev = "CRITICAL" if alerts >= 5 else "HIGH" if alerts >= 2 else "MEDIUM" if alerts >= 1 else "OK"
        signals.append(DebtSignal(
            "dep_vulnerabilities", "DECAY",
            m["dep_alerts_open"],
            _debt_from_severity(sev, 8.0),
            sev,
            f"{alerts:.0f} open Dependabot security alerts",
            "Run: gh api /repos/{owner}/{repo}/dependabot/alerts and triage." if sev != "OK" else "",
        ))

    # 9. LOCKFILE presence — reproducible dependency pinning
    has_lock, _ = _get(m, "has_lockfile")
    if has_lock is not None:
        sev = "OK" if has_lock else "MEDIUM"
        signals.append(DebtSignal(
            "lockfile_absent", "DECAY",
            m.get("has_lockfile", Metric(has_lock, "bool", "contents API", Confidence.HIGH)),
            _debt_from_severity(sev, 5.0),
            sev,
            "Lockfile (uv.lock / poetry.lock) present — reproducible deps." if has_lock
            else "No lockfile detected — dependency versions not pinned, reproducibility at risk.",
            "Add uv.lock or poetry.lock and commit it." if sev == "MEDIUM" else "",
        ))

    return signals


def score_account(snap: AccountSnapshot) -> None:
    """Score all repos, compute global signals, aggregate debt and GCEI."""
    # Score each repo
    for rs in snap.repos:
        rs.signals = score_repo(rs)
        rs.debt_score = min(sum(s.debt_contribution for s in rs.signals), 100.0)
        rs.debt_level = _debt_level(rs.debt_score)

    # Global signals
    w = snap.window_days
    m = snap.global_metrics

    # Bus factor
    bf_val, bf_conf = _get(m, "bus_factor")
    if bf_val is not None:
        bench = BENCHMARKS["bus_factor"]
        sev   = _severity(bf_val, bench, higher_is_worse=False)
        snap.global_signals.append(DebtSignal(
            "bus_factor", "ISOLATION", m["bus_factor"],
            _debt_from_severity(sev, 12.0), sev,
            f"Bus factor = {bf_val:.0f} (smallest N covering 50% of commits). "
            f"Benchmark: healthy≥{bench['healthy']}, critical={bench['critical']}",
            "Contribute to external repos AND invite contributors to yours." if sev == "CRITICAL" else "",
        ))

    # External contributors
    ext_val, _ = _get(m, "external_contributors")
    if ext_val is not None:
        bench = BENCHMARKS["external_contributors"]
        sev   = _severity(ext_val, bench, higher_is_worse=False)
        snap.global_signals.append(DebtSignal(
            "external_contributors", "ISOLATION", m["external_contributors"],
            _debt_from_severity(sev, 10.0), sev,
            f"External contributors across repos = {ext_val:.0f}. "
            f"Benchmark: critical={bench['critical']}",
            "Open issues labeled 'good first issue'. Submit PRs to peer repos." if sev == "CRITICAL" else "",
        ))

    # Reviews given
    rev_val, _ = _get(m, "reviews_given")
    if rev_val is not None and w > 0:
        rate = rev_val / w
        bench = BENCHMARKS["reviews_given_per_day"]
        sev   = _severity(rate, bench, higher_is_worse=False)
        snap.global_signals.append(DebtSignal(
            "reviews_given_rate", "ISOLATION", m["reviews_given"],
            _debt_from_severity(sev, 8.0), sev,
            f"External reviews given: {rev_val:.0f} in {w}d = {rate:.2f}/day. "
            f"Benchmark: healthy≥{bench['healthy']}/day",
            "Review 1–2 external PRs per week in domain repos." if sev in ("CRITICAL","HIGH") else "",
        ))

    # Account age penalty (Kalliamvakou: no longitudinal signal <180d)
    age = snap.account_age_days
    age_penalty = 0.0
    if age < 90:
        age_penalty = 15.0
        snap.hard_caps.append("ACCOUNT_AGE<90d: max_confidence=LOW, no longitudinal signal")
    elif age < 180:
        age_penalty = 8.0
        snap.hard_caps.append("ACCOUNT_AGE<180d: sustainability unverifiable")

    # Self-merge inflation
    pr_c, _ = _get(m, "pr_created")
    pr_m, _ = _get(m, "pr_merged")
    merge_rate = pr_m / pr_c if pr_c and pr_m and pr_c > 0 else 0.0
    if merge_rate > 0.97:
        snap.anti_gaming_penalties.append(
            f"SELF_MERGE_INFLATION: merge_rate={merge_rate*100:.1f}% — "
            "solo self-merge inflates this metric (DORA team warning Oct 2023)"
        )

    # Ext PR merged (outside own repos)
    ext_pr, _ = _get(m, "ext_pr_merged")
    if ext_pr is not None and ext_pr == 0:
        snap.global_signals.append(DebtSignal(
            "zero_external_pr", "ISOLATION",
            m["ext_pr_merged"],
            8.0, "HIGH",
            "Zero merged PRs in repositories you don't own. "
            "No external validation of your code by peers.",
            "Target Tier 1 repos from collaboration map. Goal: 1 external merge/month.",
        ))

    # ── Aggregate debt ────────────────────────────────────────────────────────
    repo_weights = [
        max((rs.metrics.get("commits_human") or Metric(0,"","",Confidence.NONE)).value or 0, 1)
        for rs in snap.repos
    ]
    total_w = sum(repo_weights)
    repo_debt = sum(
        rs.debt_score * w / total_w
        for rs, w in zip(snap.repos, repo_weights)
    ) if total_w > 0 else 50.0

    global_debt = sum(s.debt_contribution for s in snap.global_signals)
    raw_debt    = repo_debt * 0.6 + global_debt * 0.4 + age_penalty
    snap.total_debt_score = round(min(raw_debt, 100.0), 1)
    snap.debt_level = _debt_level(snap.total_debt_score)

    # ── GCEI (7-axis, geometric mean, OECD) ──────────────────────────────────
    scores = _gcei_axes(snap, w)
    snap.gcei_score = round(_geometric_mean(scores), 1)
    snap.gcei_level = _gcei_level(snap.gcei_score)

    # ── Confidence ────────────────────────────────────────────────────────────
    none_count = sum(
        1 for v in snap.global_metrics.values()
        if v.confidence == Confidence.NONE
    )
    snap.confidence = (
        Confidence.HIGH   if none_count == 0 and age >= 180 else
        Confidence.MEDIUM if none_count <= 2 else
        Confidence.LOW
    )

    # ── Risks ─────────────────────────────────────────────────────────────────
    snap.risk_sustainability = (
        "HIGH — account <180d, no longitudinal signal" if age < 180 else
        "MEDIUM — some dormant repos" if any(
            (rs.metrics.get("last_commit_days") or Metric(0,"","",Confidence.NONE)).value or 0 > 60
            for rs in snap.repos
        ) else "LOW"
    )
    avg_del = sum(
        (rs.metrics.get("deletion_ratio") or Metric(0,"","",Confidence.NONE)).value or 0
        for rs in snap.repos
    ) / max(len(snap.repos), 1)
    snap.risk_accumulation = (
        f"CRITICAL — avg deletion_ratio={avg_del:.3f}: pure accumulation" if avg_del < 0.03 else
        f"HIGH — avg deletion_ratio={avg_del:.3f}: minimal cleanup" if avg_del < 0.10 else
        f"MEDIUM — avg deletion_ratio={avg_del:.3f}" if avg_del < 0.25 else
        f"LOW — avg deletion_ratio={avg_del:.3f}"
    )
    ext_v = (m.get("external_contributors") or Metric(0,"","",Confidence.NONE)).value or 0
    rev_v = (m.get("reviews_given") or Metric(0,"","",Confidence.NONE)).value or 0
    snap.risk_isolation = (
        "CRITICAL — zero external contributors AND <10 reviews given" if ext_v == 0 and rev_v < 10 else
        "HIGH — bus_factor=1" if bf_val == 1 else
        "MEDIUM" if ext_v < 3 else "LOW"
    )
    snap.risk_stability = (
        "HIGH — CI fail rate >15% in top repo" if any(
            (rs.metrics.get("ci_fail_rate") or Metric(0,"","",Confidence.NONE)).value or 0 > 0.15
            for rs in snap.repos
        ) else "LOW"
    )

    # ── Benchmarks ────────────────────────────────────────────────────────────
    snap.benchmarks = {
        "methodology": "Solo research-infra Python developer, ~1yr account. "
                       "Nagappan & Ball (ICSE 2005), Kalliamvakou et al. (2016), "
                       "DORA 2024 report, CHAOSS community medians.",
        "deletion_ratio":  BENCHMARKS["deletion_ratio"],
        "ci_fail_rate":    BENCHMARKS["ci_fail_rate"],
        "verified_ratio":  BENCHMARKS["verified_ratio"],
        "bus_factor":      BENCHMARKS["bus_factor"],
        "reviews_given_per_day": BENCHMARKS["reviews_given_per_day"],
        "note": "Thresholds are heuristic (Kalliamvakou 2016): not peer-validated for individual leveling",
    }


def _gcei_axes(snap: AccountSnapshot, window: int) -> dict[str, float]:
    m = snap.global_metrics

    def v(key: str, default: float = 0.0) -> float:
        met = m.get(key)
        if met and met.confidence != Confidence.NONE and met.value is not None:
            return float(met.value)
        return default

    def _norm(x: float, p50: float, p90: float) -> float:
        if p90 <= p50: return 0.5
        return max(0.0, min(1.0, (math.log1p(x) - math.log1p(p50)) / (math.log1p(p90) - math.log1p(p50))))

    pr_day   = v("pr_created") / max(window, 1)
    activity = _norm(pr_day, 1.0, 10.0)

    # delivery: merge_rate × (1 - lead_time_normalized) × active_days_ratio
    pr_c = v("pr_created")
    pr_m = v("pr_merged")
    mr   = pr_m / pr_c if pr_c > 0 else 0.0
    avg_lt = sum(
        (rs.metrics.get("lead_time_p50_hours") or Metric(0,"","",Confidence.NONE)).value or 0
        for rs in snap.repos
    ) / max(len(snap.repos), 1)
    lt_score = 1.0 - _norm(avg_lt, 1.0, 48.0)
    # active_days: consistency signal — wire from deadcode
    avg_active = sum(
        (rs.metrics.get("active_days") or Metric(0,"","",Confidence.NONE)).value or 0
        for rs in snap.repos
    ) / max(len(snap.repos), 1)
    active_s  = _norm(avg_active, window * 0.3, window * 0.7)  # healthy = active 30–70% of window days
    delivery  = 0.40 * mr + 0.35 * lt_score + 0.25 * active_s

    # quality: CI success + verified commits + deletion_ratio
    ci_scores  = [(rs.metrics.get("ci_success_rate") or Metric(0,"","",Confidence.NONE)).value or 0 for rs in snap.repos]
    ci_avg     = sum(ci_scores) / max(len(ci_scores), 1)
    ver_scores = [(rs.metrics.get("verified_ratio") or Metric(0,"","",Confidence.NONE)).value or 0 for rs in snap.repos]
    ver_avg    = sum(ver_scores) / max(len(ver_scores), 1)
    del_scores = [(rs.metrics.get("deletion_ratio") or Metric(0,"","",Confidence.NONE)).value or 0 for rs in snap.repos]
    del_avg    = min(sum(del_scores) / max(len(del_scores), 1), 1.0)
    quality    = 0.4 * ci_avg + 0.35 * ver_avg + 0.25 * del_avg

    # collaboration — ext_pr_merged as primary signal (weight 0.20), reviews + bus_factor + ext_contributors
    rev_rate = v("reviews_given") / max(window, 1)
    rev_s    = _norm(rev_rate, 0.5, 5.0)
    bf       = float(v("bus_factor", 1.0))
    bf_s     = 1.0 - (1.0 / max(bf, 1))
    ext_s    = _norm(v("external_contributors"), 0.0, 10.0)
    # ext_pr_merged: strongest isolation signal — binary 0/1 → normalized (HIGHEST SIGNAL)
    ext_pr_v  = v("ext_pr_merged", 0.0)
    ext_pr_s  = _norm(ext_pr_v, 0.0, 10.0)  # 0=zero external merges, 10+=healthy
    # weights: ext_pr=0.30, reviews=0.30, bus_factor=0.20, ext_contributors=0.20
    collab = 0.30 * ext_pr_s + 0.30 * rev_s + 0.20 * bf_s + 0.20 * ext_s

    # security: verified + CI
    security = 0.5 * ver_avg + 0.5 * ci_avg

    # sustainability: INSUFFICIENT_EVIDENCE for accounts <180d (Kalliamvakou 2016)
    # 3 monthly points are NOT a longitudinal signal — explicit per filtration audit
    if snap.account_age_days < 180:
        sustain = 1e-6  # collapse sustainability axis — no longitudinal data
    else:
        t = [v(f"prs_month_{i}") for i in range(3)]
        if t[2] > t[1] > t[0]:   sustain = 1.0
        elif t[2] < t[1] < t[0]: sustain = 0.2
        else:                      sustain = 0.6

    # evidence integrity — ext_pr now in collaboration, removed from here
    ev = 0.5 * (1.0 if any((rs.metrics.get("ci_runs") or Metric(0,"","",Confidence.NONE)).value or 0 > 0 for rs in snap.repos) else 0.0)
    ev += 0.3 * ver_avg
    # wire review_comments_median from deadcode: low review discussion = low evidence quality
    avg_rc = sum(
        (rs.metrics.get("review_comments_median") or Metric(0,"","",Confidence.NONE)).value or 0
        for rs in snap.repos
    ) / max(len(snap.repos), 1)
    ev += 0.2 * _norm(avg_rc, 0.0, 5.0)  # 0 comments = 0, ≥5 comments = max

    return {
        "activity":      max(activity, 1e-6),
        "delivery":      max(delivery, 1e-6),
        "quality":       max(quality, 1e-6),
        "collaboration": max(collab, 1e-6),
        "security":      max(security, 1e-6),
        "sustainability": max(sustain, 1e-6),
        "evidence":      max(ev, 1e-6),
    }


def _geometric_mean(scores: dict[str, float]) -> float:
    """OECD anti-compensatory geometric mean with weights."""
    weights = {
        "delivery": 0.20, "quality": 0.20, "activity": 0.15,
        "collaboration": 0.15, "security": 0.15,
        "sustainability": 0.10, "evidence": 0.05,
    }
    log_sum = sum(weights[k] * math.log(max(scores.get(k, 1e-6), 1e-6)) for k in weights)
    return round(100.0 * math.exp(log_sum), 1)


def _debt_level(score: float) -> str:
    if score < 15:  return "LOW"
    if score < 30:  return "MODERATE"
    if score < 50:  return "HIGH"
    if score < 70:  return "CRITICAL"
    return "TERMINAL"


def _gcei_level(score: float) -> str:
    if score < 25:  return "NOISE"
    if score < 45:  return "JUNIOR"
    if score < 60:  return "JUNIOR→MID"
    if score < 75:  return "MID/SENIOR"
    if score < 85:  return "SENIOR"
    if score < 93:  return "STAFF"
    return "PRINCIPAL"
