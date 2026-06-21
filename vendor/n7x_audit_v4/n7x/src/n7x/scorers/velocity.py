"""
n7x.scorers.velocity
Computes rate-of-change of debt and GCEI across historical runs.
A state without its derivative is a photograph without a vector.
"""
from __future__ import annotations
import math
from typing import Any


def compute_velocity(history: list[dict]) -> dict:
    """
    Takes last N snapshots (oldest first) → velocity metrics.
    Minimum 2 runs required for any velocity signal.
    """
    if len(history) < 2:
        return {
            "schema": "n7x/velocity/v1",
            "status": "INSUFFICIENT_DATA",
            "runs_available": len(history),
            "runs_required": 2,
            "debt_velocity":    None,
            "gcei_velocity":    None,
            "debt_acceleration": None,
            "projection_90d":   None,
            "trend_verdict":    "UNKNOWN",
        }

    # Extract time-series (filter valid points)
    points: list[dict] = []
    for h in history:
        debt = h.get("total_debt_score")
        gcei = h.get("gcei_score")
        ts   = h.get("collected_at", "")
        if debt is not None and gcei is not None and ts:
            points.append({"ts": ts, "debt": float(debt), "gcei": float(gcei)})

    if len(points) < 2:
        return {"schema": "n7x/velocity/v1", "status": "INSUFFICIENT_VALID_POINTS",
                "runs_available": len(points), "runs_required": 2,
                "debt_velocity": None, "gcei_velocity": None,
                "debt_acceleration": None, "projection_90d": None,
                "trend_verdict": "UNKNOWN"}

    # Velocity: linear regression slope over all points
    # x = run index (0,1,2,...), y = metric value
    n = len(points)
    xs = list(range(n))
    debt_ys = [p["debt"] for p in points]
    gcei_ys = [p["gcei"] for p in points]

    def _slope(ys: list[float]) -> float:
        """OLS slope: Σ(xi - x̄)(yi - ȳ) / Σ(xi - x̄)²"""
        x_bar = sum(xs) / n
        y_bar = sum(ys) / n
        num = sum((xs[i] - x_bar) * (ys[i] - y_bar) for i in range(n))
        den = sum((xs[i] - x_bar) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    debt_slope = _slope(debt_ys)   # pts per run; positive = debt growing
    gcei_slope = _slope(gcei_ys)   # pts per run; positive = improving

    # Acceleration (2nd derivative proxy): slope of last half vs first half)
    def _acceleration(ys: list[float]) -> float | None:
        if n < 4:
            return None
        mid   = n // 2
        s1    = _slope(ys[:mid])
        s2    = _slope(ys[mid:])
        return s2 - s1   # positive = accelerating

    debt_accel = _acceleration(debt_ys)

    # 90-day projection (assuming ~2 runs/day → 180 runs/90d)
    RUNS_PER_90D = 180
    current_debt = debt_ys[-1]
    current_gcei = gcei_ys[-1]
    proj_debt = max(0.0, min(100.0, current_debt + debt_slope * RUNS_PER_90D))
    proj_gcei = max(0.0, min(100.0, current_gcei + gcei_slope * RUNS_PER_90D))

    # Consecutive direction check (last 3 runs)
    def _consec_direction(ys: list[float], window: int = 3) -> str:
        tail = ys[-window:] if len(ys) >= window else ys
        diffs = [tail[i+1] - tail[i] for i in range(len(tail)-1)]
        if not diffs:
            return "STABLE"
        if all(d > 0 for d in diffs):  return "UP"
        if all(d < 0 for d in diffs):  return "DOWN"
        return "MIXED"

    debt_dir = _consec_direction(debt_ys)
    gcei_dir  = _consec_direction(gcei_ys)

    # Trend verdict
    if debt_slope > 1.0 and debt_dir == "UP":
        trend_verdict = "DEBT_ACCELERATING"
    elif debt_slope > 0.3:
        trend_verdict = "DEBT_GROWING"
    elif debt_slope < -0.3 and gcei_slope > 0.3:
        trend_verdict = "IMPROVING"
    elif abs(debt_slope) <= 0.3:
        trend_verdict = "STABLE"
    else:
        trend_verdict = "MIXED"

    # Hard gate: 3 consecutive debt increases → BLOCKED
    release_blocked_by_velocity = (
        debt_dir == "UP" and debt_slope > 0.5 and len(points) >= 3
    )

    return {
        "schema":   "n7x/velocity/v1",
        "status":   "OK",
        "runs_used": n,
        "debt_velocity":     round(debt_slope, 3),   # pts/run; + = growing
        "gcei_velocity":     round(gcei_slope, 3),   # pts/run; + = improving
        "debt_acceleration": round(debt_accel, 3) if debt_accel is not None else None,
        "debt_direction_last3": debt_dir,
        "gcei_direction_last3": gcei_dir,
        "projection_90d": {
            "debt": round(proj_debt, 1),
            "gcei": round(proj_gcei, 1),
            "runs_assumed": RUNS_PER_90D,
            "note": "linear extrapolation — assumes current velocity constant",
        },
        "trend_verdict": trend_verdict,
        "release_blocked_by_velocity": release_blocked_by_velocity,
        "interpretation": (
            f"Debt {'growing' if debt_slope > 0 else 'shrinking'} "
            f"{abs(debt_slope):.2f}pts/run. "
            f"At this rate: debt={proj_debt:.0f} in 90d."
        ),
    }
