"""Cross-stream synthesis: emergent state from joining independent streams.

The repository-quality stream (scan -> normalize -> quantize -> ledger) and the
GitHub-activity stream (github_activity -> github_signals) are computed
independently. Neither stream alone can answer: *do structure and activity
agree?* This module joins them so the output of one becomes input to the other
and produces an emergent convergence state that no single module reaches alone.

First principle preserved: no quality without proof of execution. Activity never
raises the release gate (`overrides_quality=False`); it can only diagnose
divergence (e.g. activity without structure = execution theater).
"""
from __future__ import annotations

SYNTHESIS_VERSION = "cmar-synthesis/1.0.0"
TAU = 0.5  # convergence threshold shared by both stream scalars


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _repo_quality_scalar(integrated: dict) -> float:
    """Collapse the repository-quality stream to a single [0,1] readiness scalar."""
    norm = integrated.get("normalized_state") or {}
    rr = norm.get("release_readiness")
    if rr is None:
        rr = norm.get("structural_score", 0.0)
    return _clamp(rr)


def _activity_scalar(signals: dict | None) -> float:
    """Collapse the GitHub-activity stream to a single [0,1] scalar.

    Visibility-gated mean of the four activity ratios (visibility itself is a
    confidence weight, not an activity component).
    """
    if not signals:
        return 0.0
    keys = ["commit_activity_ratio", "pr_merge_ratio", "active_days_ratio", "repository_activity_ratio"]
    vals = [float(signals.get(k, 0.0) or 0.0) for k in keys]
    base = sum(vals) / len(vals)
    visibility = float(signals.get("github_visibility_signal", 0.0) or 0.0)
    return _clamp(base * visibility)


def synthesize_cross_stream(integrated: dict) -> dict | None:
    """Join the repository and GitHub streams into an emergent convergence state.

    Returns None when the GitHub stream is absent (nothing to join). The result
    is descriptive/diagnostic and never alters the release gate.
    """
    signals = integrated.get("github_signals")
    if not signals:
        return None
    q = _repo_quality_scalar(integrated)
    a = _activity_scalar(signals)
    coherence = round(1.0 - abs(q - a), 6)  # 1.0 = streams fully agree

    q_hi, a_hi = q >= TAU, a >= TAU
    if q_hi and a_hi:
        state, reason = "CONVERGENT_MATURE", "structure and activity both attested"
    elif a_hi and not q_hi:
        state, reason = "ACTIVITY_WITHOUT_STRUCTURE", "active account but repository quality unproven (execution theater risk)"
    elif q_hi and not a_hi:
        state, reason = "STRUCTURE_WITHOUT_ACTIVITY", "structure attested but recent activity is low (possible stale artifact)"
    else:
        state, reason = "IMMATURE_BOTH_STREAMS", "neither structure nor activity attested"

    # Emergent cross-stream finding: high activity masking weak structure.
    theater = bool(a_hi and (a - q) >= 0.25)

    return {
        "synthesis_version": SYNTHESIS_VERSION,
        "tau": TAU,
        "repo_quality_scalar": round(q, 6),
        "activity_scalar": round(a, 6),
        "stream_coherence": coherence,
        "convergence_state": state,
        "reason": reason,
        "activity_theater_suspected": theater,
        "overrides_quality": False,
        "emergent": True,
        "inputs": ["normalized_state.release_readiness", "github_signals"],
    }
