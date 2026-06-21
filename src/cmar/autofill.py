# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Autofill builder: measure voids/mass, apply deterministic repair, re-measure.

The completion criterion is a measured before/after delta, not a claim:
after.blocking_voids < before.blocking_voids and after.valid_mass > before.valid_mass.
"""

from __future__ import annotations

from .ledger import build_ledger
from .repair import apply_repairs
from .voids import build_void_graph


def _snapshot(repo) -> dict:
    voids = build_void_graph(repo)
    ledger = build_ledger(repo)
    return {
        "blocking_voids": voids["blocking_voids"],
        "void_count": voids["void_count"],
        "valid_mass_bytes": ledger["valid_mass_bytes"],
        "total_mass_bytes": ledger["total_mass_bytes"],
        "ledger_status": ledger["status"],
    }


def autofill(repo) -> dict:
    before = _snapshot(repo)
    repair = apply_repairs(repo)
    after = _snapshot(repo)
    improved = (after["blocking_voids"] < before["blocking_voids"]
                and after["valid_mass_bytes"] > before["valid_mass_bytes"])
    return {
        "schema_version": "cmar.autofill/v1",
        "before": before,
        "after": after,
        "created": repair["created"],
        "blocking_voids_closed": before["blocking_voids"] - after["blocking_voids"],
        "valid_mass_gained_bytes": after["valid_mass_bytes"] - before["valid_mass_bytes"],
        "improved": improved,
    }
