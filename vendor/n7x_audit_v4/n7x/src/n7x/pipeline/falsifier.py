"""
n7x.pipeline.falsifier
Adversarially tries to prove that audit output is fake, weak, or structurally invalid.
Verdict: FALSIFIED | NOT_FALSIFIED | PARTIAL
"""
from __future__ import annotations
from n7x.models import AccountSnapshot, Confidence, Metric


def _v(m: dict[str, Metric], key: str) -> float | None:
    met = m.get(key)
    if met and met.confidence != Confidence.NONE and met.value is not None:
        return float(met.value)
    return None


class FalsificationCheck:
    def __init__(self, name: str, description: str) -> None:
        self.name        = name
        self.description = description
        self.result: str = "PASS"   # PASS | FALSIFIED | INSUFFICIENT_EVIDENCE
        self.evidence: str = ""


def falsify_from_snapshot(snap: AccountSnapshot) -> dict:
    checks: list[FalsificationCheck] = []
    m  = snap.global_metrics
    rs = snap.repos

    # F1: CI absent → any quality/stability claim is unverifiable
    c = FalsificationCheck("F1_CI_ABSENT",
        "If no CI present, any quality claim is structurally unsupported")
    ci_runs_any = any(
        (r.metrics.get("ci_runs") or Metric(0,"","",Confidence.NONE)).value or 0 > 0
        for r in rs
    )
    if not ci_runs_any:
        c.result   = "FALSIFIED"
        c.evidence = "Zero CI runs across all active repos. Quality claims: VOID."
    else:
        c.result   = "PASS"
        c.evidence = "CI present in ≥1 repo."
    checks.append(c)

    # F2: merge_rate >97% with zero external reviews → self-validation only
    c = FalsificationCheck("F2_SELF_MERGE_LOOP",
        "merge_rate >97% + reviews_given <5 = no external validation loop")
    pr_c = _v(m, "pr_created") or 0
    pr_merged = _v(m, "pr_merged") or 0
    rev = _v(m, "reviews_given") or 0
    mr  = pr_merged / pr_c if pr_c > 0 else 0.0
    if mr > 0.97 and rev < 5:
        c.result   = "FALSIFIED"
        c.evidence = f"merge_rate={mr*100:.1f}%, reviews_given={rev:.0f}. Pure self-merge loop — metric is inflated."
    elif mr > 0.97:
        c.result   = "PARTIAL"
        c.evidence = f"merge_rate={mr*100:.1f}% suspicious for solo, but reviews_given={rev:.0f} ≥5."
    else:
        c.result   = "PASS"
        c.evidence = f"merge_rate={mr*100:.1f}% within acceptable range."
    checks.append(c)

    # F3: zero external PRs merged → no peer code validation
    c = FalsificationCheck("F3_ZERO_EXTERNAL_VALIDATION",
        "Zero merged PRs in repos you don't own = no external peer review of code")
    ext_pr = _v(m, "ext_pr_merged")
    if ext_pr is None:
        c.result   = "INSUFFICIENT_EVIDENCE"
        c.evidence = "ext_pr_merged: INSUFFICIENT_EVIDENCE (search API unavailable)"
    elif ext_pr == 0:
        c.result   = "FALSIFIED"
        c.evidence = "ext_pr_merged=0. No external validation. Staff/Senior claims unverifiable by peers."
    else:
        c.result   = "PASS"
        c.evidence = f"ext_pr_merged={ext_pr:.0f} ≥1."
    checks.append(c)

    # F4: bus_factor=1 → single point of failure, sustainability claim invalid
    c = FalsificationCheck("F4_BUS_FACTOR_SINGLE",
        "bus_factor=1 → any team/sustainability capability claim is structurally false")
    bf = _v(m, "bus_factor")
    if bf is None:
        c.result   = "INSUFFICIENT_EVIDENCE"
        c.evidence = "bus_factor: INSUFFICIENT_EVIDENCE"
    elif bf <= 1:
        c.result   = "FALSIFIED"
        c.evidence = f"bus_factor={bf:.0f}. Entire knowledge base in one person. Sustainability: VOID."
    else:
        c.result   = "PASS"
        c.evidence = f"bus_factor={bf:.0f} > 1."
    checks.append(c)

    # F5: account <180d → longitudinal claims invalid (Kalliamvakou 2016)
    c = FalsificationCheck("F5_INSUFFICIENT_LONGITUDINAL_DATA",
        "Account <180d → sustainability, seniority, trend claims are not longitudinally verifiable")
    age = snap.account_age_days
    if age < 180:
        c.result   = "FALSIFIED"
        c.evidence = f"account_age={age}d < 180d. Any 'sustained' or 'experienced' claim: UNVERIFIABLE."
    else:
        c.result   = "PASS"
        c.evidence = f"account_age={age}d ≥ 180d."
    checks.append(c)

    # F6: deletion_ratio ≈ 0 → pure accumulation, refactoring claims false
    c = FalsificationCheck("F6_PURE_ACCUMULATION",
        "deletion_ratio < 0.03 → code only grows, never shrinks. Refactoring claims: FALSIFIED")
    del_ratios = [
        float(r.metrics["deletion_ratio"].value)
        for r in rs
        if r.metrics.get("deletion_ratio") and
           r.metrics["deletion_ratio"].confidence != Confidence.NONE and
           r.metrics["deletion_ratio"].value is not None
    ]
    if not del_ratios:
        c.result   = "INSUFFICIENT_EVIDENCE"
        c.evidence = "deletion_ratio: INSUFFICIENT_EVIDENCE (no PR data)"
    else:
        avg_del = sum(del_ratios) / len(del_ratios)
        if avg_del < 0.03:
            c.result   = "FALSIFIED"
            c.evidence = f"avg deletion_ratio={avg_del:.4f} < 0.03. Pure accumulation. (Nagappan & Ball threshold)"
        elif avg_del < 0.10:
            c.result   = "PARTIAL"
            c.evidence = f"avg deletion_ratio={avg_del:.4f}: minimal refactoring."
        else:
            c.result   = "PASS"
            c.evidence = f"avg deletion_ratio={avg_del:.4f} ≥ 0.10."
    checks.append(c)

    # F7: GCEI >75 while collaboration=0 → geometric mean bypass check
    c = FalsificationCheck("F7_GCEI_COLLAB_PARADOX",
        "GCEI ≥ 75 while ext_pr_merged=0 and reviews_given<10 is mathematically inconsistent with geometric mean")
    gcei = snap.gcei_score
    if gcei >= 75 and (ext_pr or 0) == 0 and rev < 10:
        c.result   = "FALSIFIED"
        c.evidence = (
            f"GCEI={gcei:.1f} ≥ 75 BUT ext_pr_merged=0 and reviews_given={rev:.0f}. "
            "Collaboration axis should collapse GCEI via geometric mean. Scoring bug or data error."
        )
    else:
        c.result   = "PASS"
        c.evidence = f"GCEI={gcei:.1f}, ext_pr={ext_pr or 0:.0f}, reviews={rev:.0f} — consistent."
    checks.append(c)

    # F8: verified_ratio <0.5 in any repo → hygiene claim invalid
    c = FalsificationCheck("F8_LOW_VERIFICATION",
        "verified_ratio <0.5 in any repo → commit hygiene claims are structurally weak")
    low_ver = [
        r.name for r in rs
        if r.metrics.get("verified_ratio") and
           r.metrics["verified_ratio"].confidence != Confidence.NONE and
           (r.metrics["verified_ratio"].value or 1.0) < 0.5
    ]
    if low_ver:
        c.result   = "PARTIAL"
        c.evidence = f"Repos with verified_ratio < 0.5: {low_ver}"
    else:
        c.result   = "PASS"
        c.evidence = "All repos: verified_ratio ≥ 0.5."
    checks.append(c)

    # Aggregate verdict
    falsified = [c for c in checks if c.result == "FALSIFIED"]
    partial   = [c for c in checks if c.result == "PARTIAL"]
    insuff    = [c for c in checks if c.result == "INSUFFICIENT_EVIDENCE"]

    if falsified:
        verdict = "FALSIFIED"
    elif partial:
        verdict = "PARTIAL"
    else:
        verdict = "NOT_FALSIFIED"

    return {
        "schema":   "n7x/falsification_report/v1",
        "handle":   snap.handle,
        "collected_at": snap.collected_at,
        "checks":   [
            {"name": c.name, "description": c.description,
             "result": c.result, "evidence": c.evidence}
            for c in checks
        ],
        "summary": {
            "total":      len(checks),
            "falsified":  len(falsified),
            "partial":    len(partial),
            "insufficient": len(insuff),
            "passed":     len([c for c in checks if c.result == "PASS"]),
        },
        "falsified_checks": [c.name for c in falsified],
        "verdict": verdict,
        "interpretation": (
            "One or more structural claims are FALSIFIED by evidence. "
            "See falsified_checks for details." if verdict == "FALSIFIED" else
            "No claims fully falsified but partial concerns exist." if verdict == "PARTIAL" else
            "No claims falsified by available evidence. "
            "Note: absence of falsification ≠ proof of correctness."
        ),
    }
