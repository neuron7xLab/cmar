# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Normalization layer: heterogeneous artifact signals -> one comparable [0,1] space."""

from __future__ import annotations

from .ledger import build_ledger
from .model import clamp01, sha256_obj
from .protocol import validate_protocol
from .scan import scan_repo
from .voids import build_void_graph


def normalize(repo) -> dict:
    scan = scan_repo(repo)
    voids = build_void_graph(repo)
    ledger = build_ledger(repo)
    protocol = validate_protocol(repo)

    total = scan["total_mass_bytes"] or 1
    mass = scan["mass_by_category"]
    src = mass["source"]
    test = mass["test"]

    signals = {
        "source_mass_ratio": clamp01(src / total),
        "test_mass_ratio": clamp01(test / total),
        # test coverage of source by mass (capped at 1): tests/source
        "test_to_source_ratio": clamp01(test / src) if src else 0.0,
        "ci_presence": 1.0 if scan["presence"]["ci"] else 0.0,
        "schema_presence": 1.0 if scan["presence"]["schema"] else 0.0,
        "security_presence": 1.0 if scan["presence"]["security"] else 0.0,
        "protocol_validity": 1.0 if protocol["verdict"] == "VALID" else 0.0,
        "void_pressure": clamp01(voids["void_pressure"]),
        "valid_mass_ratio": clamp01(ledger["valid_mass_ratio"]),
        # release-blocking pressure: blocking voids normalized
        "release_blocking_pressure": clamp01(voids["blocking_voids"] / 5.0),
    }
    state = {
        "schema_version": "cmar.normalized/v1",
        "repo": scan["repo"],
        "signals": signals,
        "ledger_status": ledger["status"],
    }
    state["normalized_sha256"] = sha256_obj(signals)
    return state
