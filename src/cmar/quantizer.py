# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Quantization layer: continuous normalized metrics -> discrete release states."""

from __future__ import annotations

from .model import STATES, sha256_obj
from .normalizer import normalize

# thresholds: value >= t -> at least that state (for "more is better" metrics)
_BANDS = ((0.85, "RELEASE"), (0.6, "STRONG"), (0.35, "PARTIAL"), (0.1, "WEAK"))


def _band(value: float) -> str:
    for t, name in _BANDS:
        if value >= t:
            return name
    return "VOID"


def quantize(repo) -> dict:
    norm = normalize(repo)
    s = norm["signals"]
    # readiness: reward evidence, penalize voids/blocking pressure
    readiness = (
        0.25 * s["valid_mass_ratio"]
        + 0.20 * s["test_to_source_ratio"]
        + 0.15 * s["ci_presence"]
        + 0.10 * s["schema_presence"]
        + 0.10 * s["security_presence"]
        + 0.10 * s["protocol_validity"]
        + 0.10 * (1.0 - s["release_blocking_pressure"])
    )
    readiness = round(readiness, 6)
    overall = _band(readiness)
    # a release state requires no blocking pressure at all
    if s["release_blocking_pressure"] > 0 and overall == "RELEASE":
        overall = "STRONG"

    per_signal = {k: _band(v) for k, v in s.items() if k != "release_blocking_pressure"}
    state = {
        "schema_version": "cmar.quantized/v1",
        "repo": norm["repo"],
        "readiness_score": readiness,
        "overall_state": overall,
        "per_signal_state": per_signal,
        "states_legend": list(STATES),
    }
    state["quantized_sha256"] = sha256_obj({"r": readiness, "o": overall})
    return state
