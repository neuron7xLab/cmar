"""
n7x.scorers.target
Role-specific function value: reweights GCEI axes for concrete target.
A metric without a target function is a compass without direction.
Supported targets: research | staff | principal | ai_lab
"""
from __future__ import annotations
import math

# Weight profiles per target role
# Keys must match GCEI axis names in scorers/debt.py
TARGET_PROFILES: dict[str, dict[str, float]] = {
    "research": {
        # Anthropic/DeepMind: independent research, OSS, code quality
        "delivery":      0.15,
        "quality":       0.25,   # mypy strict, tests, CI — primary signal
        "activity":      0.10,
        "collaboration": 0.20,   # ext_pr_merged = OSS contribution
        "security":      0.10,
        "sustainability":0.10,
        "evidence":      0.10,   # research artifacts, provenance
    },
    "staff": {
        # Staff engineer: systems impact, collaboration, reliability
        "delivery":      0.20,
        "quality":       0.20,
        "activity":      0.10,
        "collaboration": 0.25,   # cross-team, bus_factor, reviews
        "security":      0.10,
        "sustainability":0.10,
        "evidence":      0.05,
    },
    "principal": {
        # Principal: ecosystem impact, sustainability, mentorship
        "delivery":      0.15,
        "quality":       0.20,
        "activity":      0.05,
        "collaboration": 0.30,   # highest weight — ecosystem influence
        "security":      0.10,
        "sustainability":0.15,
        "evidence":      0.05,
    },
    "ai_lab": {
        # Combined Anthropic+DeepMind+OpenAI signal (public JDs)
        "delivery":      0.15,
        "quality":       0.25,
        "activity":      0.10,
        "collaboration": 0.20,
        "security":      0.15,
        "sustainability":0.10,
        "evidence":      0.05,
    },
    "default": {
        # OECD baseline used in main scorer
        "delivery":      0.20,
        "quality":       0.20,
        "activity":      0.15,
        "collaboration": 0.15,
        "security":      0.15,
        "sustainability":0.10,
        "evidence":      0.05,
    },
}


def score_for_target(axes: dict[str, float], target: str = "research") -> dict:
    """
    Recompute GCEI using target-specific weights.
    axes: normalized [0,1] per axis (same as GCEI axes in debt.py)
    Returns target-adjusted score + gap analysis.
    """
    profile = TARGET_PROFILES.get(target, TARGET_PROFILES["default"])

    # Validate weights sum to 1.0
    weight_sum = sum(profile.values())
    assert abs(weight_sum - 1.0) < 1e-6, f"weights sum={weight_sum} ≠ 1.0 for {target}"

    # Geometric mean (anti-compensatory — same as main scorer)
    log_sum = sum(
        profile[k] * math.log(max(axes.get(k, 1e-6), 1e-6))
        for k in profile
    )
    target_gcei = round(100.0 * math.exp(log_sum), 1)

    # Gap analysis: which axes most drag the target score
    gaps: list[dict] = []
    for axis, weight in sorted(profile.items(), key=lambda x: -x[1]):
        val     = axes.get(axis, 0.0)
        # Marginal gain if this axis went to 1.0
        axes_boosted = dict(axes)
        axes_boosted[axis] = 1.0
        log_boosted = sum(
            profile[k] * math.log(max(axes_boosted.get(k, 1e-6), 1e-6))
            for k in profile
        )
        boosted_gcei = 100.0 * math.exp(log_boosted)
        marginal_gain = boosted_gcei - target_gcei
        gaps.append({
            "axis":          axis,
            "current_value": round(val, 4),
            "weight":        weight,
            "marginal_gain": round(marginal_gain, 1),
            "priority":      "HIGH" if marginal_gain > 10 else "MEDIUM" if marginal_gain > 5 else "LOW",
        })

    gaps.sort(key=lambda x: -x["marginal_gain"])

    # Level using same thresholds as main scorer
    def _level(s: float) -> str:
        if s < 25:  return "NOISE"
        if s < 45:  return "JUNIOR"
        if s < 60:  return "JUNIOR→MID"
        if s < 75:  return "MID/SENIOR"
        if s < 85:  return "SENIOR"
        if s < 93:  return "STAFF"
        return "PRINCIPAL"

    top_gaps = [g for g in gaps if g["priority"] == "HIGH"]
    return {
        "schema":       "n7x/target_score/v1",
        "target":       target,
        "target_gcei":  target_gcei,
        "target_level": _level(target_gcei),
        "weights_used": profile,
        "gap_analysis": gaps,
        "top_priority_gaps": top_gaps,
        "interpretation": (
            f"For target='{target}': GCEI={target_gcei:.0f} [{_level(target_gcei)}]. "
            f"Top gap: {gaps[0]['axis']}={gaps[0]['current_value']:.2f} "
            f"(+{gaps[0]['marginal_gain']:.0f}pts if fixed)."
            if gaps else "No axes available."
        ),
    }


def compare_targets(axes: dict[str, float]) -> dict:
    """Score against all target profiles simultaneously."""
    results = {}
    for t in TARGET_PROFILES:
        results[t] = score_for_target(axes, t)
    best   = max(results, key=lambda t: results[t]["target_gcei"])
    worst  = min(results, key=lambda t: results[t]["target_gcei"])
    return {
        "schema":  "n7x/target_comparison/v1",
        "targets": {t: {
            "gcei":  results[t]["target_gcei"],
            "level": results[t]["target_level"],
        } for t in results},
        "best_fit":  best,
        "worst_fit": worst,
        "spread": round(
            results[best]["target_gcei"] - results[worst]["target_gcei"], 1
        ),
    }
