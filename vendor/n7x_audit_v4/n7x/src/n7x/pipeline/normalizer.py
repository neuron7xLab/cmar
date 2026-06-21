"""
n7x.pipeline.normalizer
Maps heterogeneous signals → normalized [0,1] space.
Every output field: value in [0,1] + source signal + confidence.
Fail-closed: missing input → 0.0 with confidence=NONE.
"""
from __future__ import annotations
import math
from n7x.models import AccountSnapshot, Confidence, Metric


def _v(m: dict[str, Metric], key: str, default: float = 0.0) -> tuple[float, str]:
    met = m.get(key)
    if met and met.confidence != Confidence.NONE and met.value is not None:
        return float(met.value), met.confidence.value
    return default, "NONE"


def _norm_log(x: float, p50: float, p90: float) -> float:
    if p90 <= p50:
        return 0.5
    return max(0.0, min(1.0,
        (math.log1p(x) - math.log1p(p50)) / (math.log1p(p90) - math.log1p(p50))
    ))


def normalize_from_snapshot(snap: AccountSnapshot) -> dict:
    """
    Normalize AccountSnapshot → normalized_state.json
    All values in [0,1]. Higher = better (health), except where noted.
    """
    m  = snap.global_metrics
    rs = snap.repos

    def repo_avg(field: str) -> tuple[float, str]:
        vals = []
        for r in rs:
            met = r.metrics.get(field)
            if met and met.confidence != Confidence.NONE and met.value is not None:
                vals.append(float(met.value))
        if not vals:
            return 0.0, "NONE"
        return sum(vals) / len(vals), "MEDIUM"

    # ── Activity ─────────────────────────────────────────────────────────────
    pr_c, pr_c_conf   = _v(m, "pr_created")
    pr_day = pr_c / max(snap.window_days, 1)
    activity_norm = _norm_log(pr_day, 1.0, 10.0)

    # ── Delivery ──────────────────────────────────────────────────────────────
    pr_merged_v, _    = _v(m, "pr_merged")
    merge_rate        = pr_merged_v / pr_c if pr_c > 0 else 0.0
    lt_avg, lt_conf   = repo_avg("lead_time_p50_hours")
    lt_norm           = 1.0 - _norm_log(lt_avg, 1.0, 48.0)
    active_avg, _     = repo_avg("active_days")
    active_norm       = _norm_log(active_avg, snap.window_days * 0.3, snap.window_days * 0.7)

    # ── Quality ───────────────────────────────────────────────────────────────
    ci_avg, ci_conf   = repo_avg("ci_success_rate")
    ver_avg, ver_conf = repo_avg("verified_ratio")
    del_avg, del_conf = repo_avg("deletion_ratio")
    del_norm          = min(del_avg, 1.0)          # higher deletion_ratio = healthier
    ci_runs_avg, _    = repo_avg("ci_runs")
    ci_presence       = 1.0 if ci_runs_avg > 0 else 0.0

    # ── Collaboration ─────────────────────────────────────────────────────────
    rev_v, rev_conf   = _v(m, "reviews_given")
    rev_rate          = rev_v / max(snap.window_days, 1)
    rev_norm          = _norm_log(rev_rate, 0.5, 5.0)
    bf_v, bf_conf     = _v(m, "bus_factor", 1.0)
    bf_norm           = 1.0 - (1.0 / max(bf_v, 1))
    ext_v, ext_conf   = _v(m, "external_contributors")
    ext_norm          = _norm_log(ext_v, 0.0, 10.0)
    ext_pr_v, _       = _v(m, "ext_pr_merged")
    ext_pr_norm       = _norm_log(ext_pr_v, 0.0, 10.0)

    # ── Security ──────────────────────────────────────────────────────────────
    dep_alerts_avg, _ = repo_avg("dep_alerts_open")
    # invert: 0 alerts = 1.0
    sec_alerts_norm   = max(0.0, 1.0 - _norm_log(dep_alerts_avg, 0.0, 10.0))
    lockfile_avg, _   = repo_avg("has_lockfile")
    security_norm     = 0.5 * ver_avg + 0.3 * ci_avg + 0.2 * sec_alerts_norm

    # ── Sustainability ────────────────────────────────────────────────────────
    age              = snap.account_age_days
    if age < 180:
        sustain_norm = 0.0   # INSUFFICIENT_EVIDENCE per Kalliamvakou
        sustain_conf = "NONE"
    else:
        t = [float(_v(m, f"prs_month_{i}")[0]) for i in range(3)]
        if t[2] > t[1] > t[0]:   sustain_norm, sustain_conf = 1.0, "MEDIUM"
        elif t[2] < t[1] < t[0]: sustain_norm, sustain_conf = 0.2, "MEDIUM"
        else:                      sustain_norm, sustain_conf = 0.6, "MEDIUM"

    # ── Void pressure (inverse of health) ────────────────────────────────────
    # High void pressure = many blocking signals near-zero
    void_signals = [
        ci_presence,
        ver_avg,
        del_norm,
        ext_pr_norm,
        merge_rate,
    ]
    avg_health   = sum(void_signals) / len(void_signals)
    void_pressure = round(1.0 - avg_health, 4)  # 0=no void, 1=full void

    # ── Debt as normalized signal ─────────────────────────────────────────────
    debt_norm     = round(snap.total_debt_score / 100.0, 4)  # higher = more debt
    gcei_norm     = round(snap.gcei_score / 100.0, 4)        # higher = better

    # ── Release blocking pressure ─────────────────────────────────────────────
    blocking = []
    if ci_presence < 0.5:
        blocking.append("NO_CI")
    if ext_pr_norm == 0.0:
        blocking.append("ZERO_EXTERNAL_PR")
    if bf_v <= 1.0:
        blocking.append("BUS_FACTOR_1")
    if age < 180:
        blocking.append("INSUFFICIENT_LONGITUDINAL_DATA")
    if del_norm < 0.05:
        blocking.append("PURE_ACCUMULATION")
    release_blocking_pressure = round(len(blocking) / 5.0, 4)  # 0–1

    return {
        "schema":   "n7x/normalized_state/v1",
        "handle":   snap.handle,
        "collected_at": snap.collected_at,
        "window_days":  snap.window_days,
        "account_age_days": age,
        "signals": {
            # Activity
            "activity_norm":          {"value": round(activity_norm, 4), "source": "pr_created/day", "confidence": pr_c_conf},
            # Delivery
            "merge_rate":             {"value": round(merge_rate, 4),    "source": "pr_merged/pr_created", "confidence": "HIGH"},
            "lead_time_norm":         {"value": round(lt_norm, 4),       "source": "lead_time_p50_hours (inverted)", "confidence": lt_conf},
            "active_days_norm":       {"value": round(active_norm, 4),   "source": "active_days/window", "confidence": "MEDIUM"},
            # Quality
            "ci_success_rate":        {"value": round(ci_avg, 4),        "source": "ci_success_rate (repo avg)", "confidence": ci_conf},
            "ci_presence":            {"value": ci_presence,              "source": "ci_runs > 0", "confidence": "HIGH"},
            "verified_ratio":         {"value": round(ver_avg, 4),       "source": "commit.verification.verified", "confidence": ver_conf},
            "deletion_ratio_norm":    {"value": round(del_norm, 4),      "source": "deletions/additions (Nagappan & Ball)", "confidence": del_conf},
            # Collaboration
            "reviews_given_norm":     {"value": round(rev_norm, 4),      "source": "reviews_given/day", "confidence": rev_conf},
            "bus_factor_norm":        {"value": round(bf_norm, 4),       "source": "CHAOSS Contributor Absence Factor", "confidence": bf_conf},
            "external_contributors_norm": {"value": round(ext_norm, 4), "source": "contributors API", "confidence": ext_conf},
            "ext_pr_merged_norm":     {"value": round(ext_pr_norm, 4),  "source": "search: merged PRs outside own repos", "confidence": "MEDIUM"},
            # Security
            "security_norm":          {"value": round(security_norm, 4), "source": "verified+CI+dep_alerts composite", "confidence": "MEDIUM"},
            "dep_alerts_norm":        {"value": round(sec_alerts_norm, 4), "source": "dependabot alerts (inverted)", "confidence": "MEDIUM"},
            # Sustainability
            "sustainability_norm":    {"value": round(sustain_norm, 4), "source": "monthly_trend monotonicity", "confidence": sustain_conf},
            # Composite
            "void_pressure":          {"value": void_pressure,           "source": "1 - avg(health signals)", "confidence": "MEDIUM"},
            "debt_norm":              {"value": debt_norm,                "source": "total_debt_score/100", "confidence": "HIGH"},
            "gcei_norm":              {"value": gcei_norm,                "source": "gcei_score/100", "confidence": "HIGH"},
            "release_blocking_pressure": {"value": release_blocking_pressure, "source": f"{len(blocking)}/5 blocking signals", "confidence": "HIGH"},
        },
        "blocking_signals": blocking,
        "blocking_count":   len(blocking),
    }
