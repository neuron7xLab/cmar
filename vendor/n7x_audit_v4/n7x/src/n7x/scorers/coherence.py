"""
n7x.scorers.coherence
Computes variance across GCEI axes and detects structural anomalies.
High delivery + zero collaboration = structural anomaly, not just low score.
Dispersion between axes carries more information than the mean.
"""
from __future__ import annotations
import math
import statistics


def compute_coherence(axes: dict[str, float]) -> dict:
    """
    axes: dict of axis_name → normalized [0,1] score
    Returns: variance, anomaly patterns, coherence verdict.
    """
    if not axes:
        return {"schema": "n7x/coherence/v1", "status": "NO_DATA",
                "variance": None, "anomalies": [], "verdict": "UNKNOWN"}

    vals  = list(axes.values())
    mean  = statistics.mean(vals)
    var   = statistics.variance(vals) if len(vals) > 1 else 0.0
    stdev = math.sqrt(var)

    # Detect structural anomaly patterns
    anomalies: list[dict] = []

    def _v(key: str) -> float:
        return axes.get(key, 0.0)

    # Pattern A: high delivery + void collaboration
    if _v("delivery") > 0.60 and _v("collaboration") < 0.20:
        anomalies.append({
            "pattern": "ISOLATED_DELIVERY",
            "severity": "CRITICAL",
            "description": (
                f"delivery={_v('delivery'):.2f} HIGH but collaboration={_v('collaboration'):.2f} VOID. "
                "Fast solo ship with zero external loop. System cannot self-validate."
            ),
            "axes": ["delivery", "collaboration"],
        })

    # Pattern B: high activity + low quality
    if _v("activity") > 0.70 and _v("quality") < 0.40:
        anomalies.append({
            "pattern": "VOLUME_WITHOUT_QUALITY",
            "severity": "HIGH",
            "description": (
                f"activity={_v('activity'):.2f} HIGH but quality={_v('quality'):.2f} LOW. "
                "High PR volume masking low CI/verification discipline."
            ),
            "axes": ["activity", "quality"],
        })

    # Pattern C: high security + zero evidence
    if _v("security") > 0.60 and _v("evidence") < 0.20:
        anomalies.append({
            "pattern": "SECURITY_WITHOUT_EVIDENCE",
            "severity": "MEDIUM",
            "description": (
                f"security={_v('security'):.2f} claimed HIGH but evidence={_v('evidence'):.2f} VOID. "
                "Security posture not externally verifiable."
            ),
            "axes": ["security", "evidence"],
        })

    # Pattern D: all axes medium — false coherence (everything average = nothing exceptional)
    all_medium = all(0.35 < v < 0.65 for v in vals)
    if all_medium and len(vals) >= 5:
        anomalies.append({
            "pattern": "FALSE_COHERENCE",
            "severity": "LOW",
            "description": (
                "All axes in [0.35, 0.65] — no outliers. "
                "Appears balanced but may indicate generalist plateau with no depth."
            ),
            "axes": list(axes.keys()),
        })

    # Pattern E: sustainability void with everything else strong
    non_sust = {k: v for k, v in axes.items() if k != "sustainability"}
    if non_sust and statistics.mean(non_sust.values()) > 0.60 and _v("sustainability") < 0.10:
        anomalies.append({
            "pattern": "UNSUSTAINABLE_PEAK",
            "severity": "HIGH",
            "description": (
                f"sustainability={_v('sustainability'):.2f} VOID while other axes avg "
                f"{statistics.mean(non_sust.values()):.2f}. "
                "Strong current state with no longitudinal evidence. "
                "Could be sprint artifact, not sustained capability."
            ),
            "axes": ["sustainability"],
        })

    # Coherence verdict
    if stdev > 0.35:
        verdict = "INCOHERENT"   # extreme spread between axes
    elif stdev > 0.20:
        verdict = "POLARIZED"    # noticeable imbalance
    elif stdev > 0.10:
        verdict = "MODERATE"
    else:
        verdict = "COHERENT"

    # Strongest and weakest axes
    sorted_axes = sorted(axes.items(), key=lambda x: x[1])
    weakest  = sorted_axes[:2]
    strongest = sorted_axes[-2:]

    return {
        "schema":   "n7x/coherence/v1",
        "status":   "OK",
        "mean":     round(mean, 4),
        "variance": round(var, 4),
        "stdev":    round(stdev, 4),
        "axes":     {k: round(v, 4) for k, v in axes.items()},
        "weakest":  [{"axis": k, "value": round(v, 4)} for k, v in weakest],
        "strongest":[{"axis": k, "value": round(v, 4)} for k, v in strongest],
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "critical_anomalies": len([a for a in anomalies if a["severity"] == "CRITICAL"]),
        "verdict": verdict,
        "interpretation": (
            f"Axis spread: stdev={stdev:.2f}. "
            f"Verdict: {verdict}. "
            f"{len(anomalies)} structural anomaly(ies) detected."
        ),
    }
