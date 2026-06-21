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


def compute_expansion(ledger: dict, history: list[dict] | None = None, horizon: int = 5) -> dict:
    """Project valid_mass and blocking_voids `horizon` iterations forward."""
    history = list(history or [])
    if horizon <= 0:
        horizon = 5

    cur_mass = _num(ledger.get("valid_mass_bytes"))
    cur_voids = _num(ledger.get("blocking_voids"))
    total_voids = _num(ledger.get("voids_detected"))

    # --- velocity ---
    series = [*history, {"valid_mass_bytes": cur_mass, "blocking_voids": cur_voids}]
    if len(series) >= 2:
        steps = len(series) - 1
        mass_velocity = (_num(series[-1]["valid_mass_bytes"]) - _num(series[0]["valid_mass_bytes"])) / steps
        voids_closed_per_iter = (_num(series[0]["blocking_voids"]) - _num(series[-1]["blocking_voids"])) / steps
        confidence = "HIGH"
        measured_closure_rate = round(voids_closed_per_iter, 6)
    else:
        mass_velocity = float(_BASELINE_MASS_VELOCITY)
        voids_closed_per_iter = _BASELINE_VOIDS_PER_ITER
        confidence = "LOW"
        measured_closure_rate = None  # no history -> closure rate is unmeasured

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
