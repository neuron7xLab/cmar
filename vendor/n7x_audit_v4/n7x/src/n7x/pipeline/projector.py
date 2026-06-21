"""
n7x.pipeline.projector
90-day forward projection: if velocity unchanged, where will I be?
Integrates velocity + coherence + target for full epistemic picture.
"""
from __future__ import annotations
from n7x.scorers.velocity import compute_velocity
from n7x.scorers.coherence import compute_coherence
from n7x.scorers.target import compare_targets, score_for_target


def project(
    history: list[dict],
    current_axes: dict[str, float],
    target: str = "research",
) -> dict:
    """
    history: list of past snapshots (oldest first)
    current_axes: normalized [0,1] per GCEI axis
    target: role target for gap analysis
    """
    vel  = compute_velocity(history)
    coh  = compute_coherence(current_axes)
    tgt  = score_for_target(current_axes, target)
    comp = compare_targets(current_axes)

    # What needs to change for next level?
    current_gcei  = tgt["target_gcei"]
    current_level = tgt["target_level"]
    level_thresholds = [25, 45, 60, 75, 85, 93, 100]
    next_threshold = next((t for t in level_thresholds if t > current_gcei), 100)
    pts_to_next_level = round(next_threshold - current_gcei, 1)

    # Estimated runs to next level at current velocity
    gcei_vel = vel.get("gcei_velocity") or 0.0
    if gcei_vel > 0:
        runs_to_next = round(pts_to_next_level / gcei_vel)
        days_to_next = round(runs_to_next / 2)  # 2 runs/day
    else:
        runs_to_next = None
        days_to_next = None

    # Critical path: which single axis fix gives most GCEI gain?
    top_gaps = tgt.get("top_priority_gaps", [])
    critical_path = top_gaps[0] if top_gaps else None

    # Blocking summary: all reasons release is blocked right now
    blocks: list[str] = []
    if vel.get("release_blocked_by_velocity"):
        blocks.append(f"DEBT_TREND_UP: velocity={vel.get('debt_velocity'):.2f}pts/run")
    if coh.get("critical_anomalies", 0) > 0:
        for a in coh.get("anomalies", []):
            if a["severity"] == "CRITICAL":
                blocks.append(f"STRUCTURAL_ANOMALY:{a['pattern']}")

    return {
        "schema":  "n7x/projection/v1",
        "target":  target,

        # Current state
        "current": {
            "gcei":  current_gcei,
            "level": current_level,
            "pts_to_next_level": pts_to_next_level,
        },

        # Velocity
        "velocity": {
            "debt_velocity":    vel.get("debt_velocity"),
            "gcei_velocity":    vel.get("gcei_velocity"),
            "debt_direction":   vel.get("debt_direction_last3"),
            "gcei_direction":   vel.get("gcei_direction_last3"),
            "trend_verdict":    vel.get("trend_verdict"),
            "projection_90d":   vel.get("projection_90d"),
        },

        # Coherence
        "coherence": {
            "verdict":     coh.get("verdict"),
            "stdev":       coh.get("stdev"),
            "anomalies":   coh.get("anomalies", []),
            "weakest":     coh.get("weakest", []),
            "strongest":   coh.get("strongest", []),
        },

        # Target gap
        "target_gap": {
            "critical_path":    critical_path,
            "all_gaps":         tgt.get("gap_analysis", []),
            "days_to_next_level": days_to_next,
            "runs_to_next_level": runs_to_next,
        },

        # Cross-target comparison
        "target_comparison": comp.get("targets", {}),
        "best_fit_role":     comp.get("best_fit"),

        # Release blocks
        "release_blocks":    blocks,
        "release_blocked":   len(blocks) > 0,

        # Plain language verdict
        "verdict": _plain_verdict(vel, coh, tgt, blocks, days_to_next),
    }


def _plain_verdict(vel: dict, coh: dict, tgt: dict, blocks: list, days: int | None) -> str:
    parts: list[str] = []

    tv = vel.get("trend_verdict", "UNKNOWN")
    if tv == "DEBT_ACCELERATING":
        parts.append("Debt accelerating — direction reversed, not just slow.")
    elif tv == "DEBT_GROWING":
        parts.append("Debt growing. At current rate: blocked in <90d.")
    elif tv == "IMPROVING":
        parts.append("Trajectory positive — debt falling, GCEI rising.")
    elif tv == "STABLE":
        parts.append("State stable. No movement.")
    else:
        parts.append("Insufficient history for trend.")

    if coh.get("critical_anomalies", 0) > 0:
        for a in coh.get("anomalies", []):
            if a["severity"] == "CRITICAL":
                parts.append(f"Structural anomaly: {a['pattern']}.")

    top_gaps = tgt.get("top_priority_gaps", [])
    if top_gaps:
        g = top_gaps[0]
        parts.append(
            f"Highest leverage fix: {g['axis']} (currently {g['current_value']:.2f}) "
            f"→ +{g['marginal_gain']:.0f}pts GCEI if resolved."
        )

    if days is not None:
        parts.append(f"At current velocity: next level in ~{days}d.")
    else:
        parts.append("GCEI not improving — next level: indefinite without action.")

    return " ".join(parts)
