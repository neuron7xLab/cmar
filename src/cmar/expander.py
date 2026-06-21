"""Future-state projector: turns CMAR from a present-state validator into a
forward projector. Computes `potential_mass` and an `expansion_vector` from the
current ledger plus optional history of prior ledger snapshots.

All outputs are computed, never assigned: `potential_mass` from projected
states, `entropy_estimate` deterministically from voids, `expansion_verdict`
derived from velocity signs.
"""
from __future__ import annotations

SCHEMA = "cmar/expansion_report/v1"
# Conservative baseline when no history exists: the observed autofill delta
# (seed valid_mass 119 -> 1188 in one iteration) and one void closed per step.
_BASELINE_MASS_VELOCITY = 1188 - 119  # 1069
_BASELINE_VOIDS_PER_ITER = 1.0


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float(default)


def _ols(ys):
    """OLS over equally-spaced x=0..n-1. Returns (slope, r2). Evidence: OLS beats
    the two-endpoint estimator under noise (study mean err 0.131 vs 0.163)."""
    n = len(ys)
    if n < 2:
        return 0.0, 1.0
    xs = list(range(n))
    mx = (n - 1) / 2.0
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    return slope, r2


def compute_expansion(ledger: dict, history: list[dict] | None = None, horizon: int = 5) -> dict:
    """Project valid_mass and blocking_voids `horizon` iterations forward.

    Velocity is estimated by OLS over the full (history + current) series; the
    confidence is gated on fit quality (R^2), not point count alone, per the
    findings in studies/expansion_validity/REPORT.md.
    """
    history = list(history or [])
    if horizon <= 0:
        horizon = 5

    cur_mass = _num(ledger.get("valid_mass_bytes"))
    cur_voids = _num(ledger.get("blocking_voids"))
    total_voids = _num(ledger.get("voids_detected"))

    # --- velocity (OLS over the measured series) ---
    series = [*history, {"valid_mass_bytes": cur_mass, "blocking_voids": cur_voids}]
    n = len(series)
    fit_quality = None
    nonlinearity_warning = None
    if n >= 2:
        mass_series = [_num(s.get("valid_mass_bytes")) for s in series]
        voids_series = [_num(s.get("blocking_voids")) for s in series]
        mass_velocity, fit_quality = _ols(mass_series)
        voids_slope, _ = _ols(voids_series)
        voids_closed_per_iter = -voids_slope  # closing == voids decreasing
        measured_closure_rate = round(voids_closed_per_iter, 6)
        model = "linear_ols"
        if n < 3:
            confidence = "LOW"  # too few points to assess fit
        elif fit_quality >= 0.9:
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"
        if fit_quality is not None and fit_quality < 0.9:
            nonlinearity_warning = (
                f"linear fit weak (R2={round(fit_quality, 4)}); potential_mass magnitude "
                "is unreliable on this non-linear trajectory — trust direction only")
    else:
        mass_velocity = float(_BASELINE_MASS_VELOCITY)
        voids_closed_per_iter = _BASELINE_VOIDS_PER_ITER
        confidence = "LOW"
        measured_closure_rate = None  # no history -> closure rate is unmeasured
        model = "baseline_autofill_delta"

    # --- projected states ---
    projected = []
    for i in range(1, horizon + 1):
        mass_i = max(int(round(cur_mass + i * mass_velocity)), 0)
        voids_i = max(int(round(cur_voids - i * voids_closed_per_iter)), 0)
        projected.append({"iteration": i, "valid_mass_bytes": mass_i, "blocking_voids": voids_i})

    potential_mass = max(projected[-1]["valid_mass_bytes"], 0)

    # --- verdict (derived from velocity signs, never assigned) ---
    if mass_velocity < 0:
        verdict = "DIVERGING"
    elif voids_closed_per_iter < 0:  # blocking voids trending up
        verdict = "DIVERGING"
    elif mass_velocity == 0 and voids_closed_per_iter == 0:
        verdict = "STABLE"
    else:
        verdict = "CONVERGING"

    # --- deterministic entropy ---
    entropy = round(cur_voids / (total_voids + 1.0), 6)
    entropy = max(0.0, min(1.0, entropy))

    interp = {
        "CONVERGING": f"mass grows ~{int(round(mass_velocity))}/iter and voids do not increase; potential_mass={potential_mass} at horizon {horizon}",
        "STABLE": "no projected change in mass or voids",
        "DIVERGING": "a tracked trend is negative (mass shrinking or voids growing) — system degrading",
    }[verdict]
    if confidence == "LOW":
        interp = "[LOW confidence: conservative baseline, no history] " + interp

    return {
        "schema": SCHEMA,
        "horizon": horizon,
        "confidence": confidence,
        "model": model,
        "fit_quality": round(fit_quality, 6) if fit_quality is not None else None,
        "nonlinearity_warning": nonlinearity_warning,
        "current": {
            "valid_mass_bytes": int(cur_mass),
            "blocking_voids": int(cur_voids),
            "void_closure_rate": measured_closure_rate,
        },
        "velocity": {
            "valid_mass_per_iteration": round(mass_velocity, 6),
            "voids_closed_per_iteration": round(voids_closed_per_iter, 6),
        },
        "projected_states": projected,
        "potential_mass": potential_mass,
        "expansion_verdict": verdict,
        "entropy_estimate": entropy,
        "interpretation": interp,
    }
