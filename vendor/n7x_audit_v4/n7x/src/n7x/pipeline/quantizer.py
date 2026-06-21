"""
n7x.pipeline.quantizer
Compresses normalized [0,1] signals → discrete state.
States: VOID | WEAK | PARTIAL | STRONG | RELEASE
Deterministic: same input → same output always.
"""
from __future__ import annotations

STATES = ["VOID", "WEAK", "PARTIAL", "STRONG", "RELEASE"]


def _sig(norm: dict, key: str) -> float:
    return float(norm.get("signals", {}).get(key, {}).get("value", 0.0))


def quantize(normalized: dict) -> dict:
    """
    Map normalized_state → quantized_state.
    Each axis → discrete bucket.
    Composite → VOID/WEAK/PARTIAL/STRONG/RELEASE.
    """
    s = normalized.get("signals", {})

    def v(key: str) -> float:
        return float(s.get(key, {}).get("value", 0.0))

    def _bucket(val: float) -> str:
        """Map [0,1] → discrete state."""
        if val < 0.20: return "VOID"
        if val < 0.40: return "WEAK"
        if val < 0.60: return "PARTIAL"
        if val < 0.80: return "STRONG"
        return "RELEASE"

    axes = {
        "activity":       v("activity_norm"),
        "delivery":       (v("merge_rate") * 0.40 + v("lead_time_norm") * 0.35 + v("active_days_norm") * 0.25),
        "quality":        (v("ci_success_rate") * 0.40 + v("verified_ratio") * 0.35 + v("deletion_ratio_norm") * 0.25),
        "collaboration":  (v("ext_pr_merged_norm") * 0.30 + v("reviews_given_norm") * 0.30 + v("bus_factor_norm") * 0.20 + v("external_contributors_norm") * 0.20),
        "security":       v("security_norm"),
        "sustainability": v("sustainability_norm"),
        "evidence":       (v("ci_presence") * 0.50 + v("verified_ratio") * 0.30 + v("ext_pr_merged_norm") * 0.20),
    }

    buckets = {k: _bucket(val) for k, val in axes.items()}

    # Composite: geometric-mean-like — worst axis has disproportionate pull
    import math
    weights = {"delivery": 0.20, "quality": 0.20, "activity": 0.15,
               "collaboration": 0.15, "security": 0.15, "sustainability": 0.10, "evidence": 0.05}
    log_sum = sum(weights[k] * math.log(max(axes[k], 1e-6)) for k in weights)
    composite_val = math.exp(log_sum)
    composite_state = _bucket(composite_val)

    # Hard overrides — fail-closed
    blocking = normalized.get("blocking_signals", [])
    hard_overrides: list[str] = []

    if "NO_CI" in blocking:
        composite_state = "VOID"
        hard_overrides.append("NO_CI → forced VOID")
    if "ZERO_EXTERNAL_PR" in blocking and composite_state in ("RELEASE", "STRONG"):
        composite_state = "PARTIAL"
        hard_overrides.append("ZERO_EXTERNAL_PR → capped at PARTIAL")
    if "INSUFFICIENT_LONGITUDINAL_DATA" in blocking and composite_state in ("RELEASE", "STRONG"):
        composite_state = "PARTIAL"
        hard_overrides.append("INSUFFICIENT_LONGITUDINAL_DATA → capped at PARTIAL")

    # State index for trend tracking
    state_idx = STATES.index(composite_state) if composite_state in STATES else 0

    return {
        "schema": "n7x/quantized_state/v1",
        "handle": normalized.get("handle"),
        "collected_at": normalized.get("collected_at"),
        "axes": {k: {"value": round(axes[k], 4), "state": buckets[k]} for k in axes},
        "composite": {
            "value":       round(composite_val, 4),
            "state":       composite_state,
            "state_index": state_idx,
        },
        "blocking_signals": blocking,
        "hard_overrides":   hard_overrides,
        "release_ready":    composite_state == "RELEASE",
        "verdict": (
            "RELEASE_BLOCKED"  if composite_state in ("VOID", "WEAK") else
            "RELEASE_CONDITIONAL" if composite_state == "PARTIAL" else
            "RELEASE_CANDIDATE" if composite_state == "STRONG" else
            "RELEASE_READY"
        ),
    }
