# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Falsification evaluator: try to prove the artifact state is fake or invalid.

Each check is an attempt to refute the repository's integrity. A check that fires
is a real defect. Verdict: FALSIFIED (a hard structural lie), PARTIAL (weaknesses
but no lie), NOT_FALSIFIED (survived every attack).
"""

from __future__ import annotations

from .integrator import integrate
from .ledger import build_ledger
from .model import sha256_obj
from .protocol import validate_protocol
from .scan import scan_repo
from .voids import build_void_graph


def falsify(repo) -> dict:
    scan = scan_repo(repo)
    voids = build_void_graph(repo)
    ledger = build_ledger(repo)
    protocol = validate_protocol(repo)
    integrated = integrate(repo)
    mass = scan["mass_by_category"]
    total = scan["total_mass_bytes"]

    hard: list[str] = []   # structural lies -> FALSIFIED
    weak: list[str] = []   # weaknesses -> PARTIAL

    # hard lies
    if ledger["valid_mass_bytes"] > total:
        hard.append("ledger valid_mass exceeds total mass")
    if integrated["release_verdict"] == "RELEASE_READY" and voids["blocking_voids"] > 0:
        hard.append("release marked ready while blocking voids exist")
    if protocol["verdict"] == "INVALID":
        hard.append("protocol invalid: " + "; ".join(protocol["violations"]))
    # ledger chain integrity
    prev = "0" * 64
    for e in ledger["chain"]:
        if e["prev_hash"] != prev or sha256_obj({"prev": prev, "payload": {"category": e["category"], "bytes": e["bytes"]}}) != e["record_hash"]:
            hard.append("ledger hash chain broken")
            break
        prev = e["record_hash"]

    # weaknesses
    if not scan["presence"]["tests"]:
        weak.append("no tests")
    if not scan["presence"]["ci"]:
        weak.append("no CI")
    if not scan["presence"]["schema"]:
        weak.append("no schemas")
    docs_mass = mass["docs"]
    exec_mass = mass["source"] + mass["test"]
    if total and docs_mass > exec_mass and exec_mass < 0.2 * total:
        weak.append("docs-heavy artifact with little executable mass")

    verdict = "FALSIFIED" if hard else ("PARTIAL" if weak else "NOT_FALSIFIED")
    result = {
        "schema_version": "cmar.falsification/v1",
        "repo": scan["repo"],
        "hard_findings": hard,
        "weak_findings": weak,
        "verdict": verdict,
    }
    result["falsification_sha256"] = sha256_obj({"v": verdict, "h": hard, "w": weak})
    return result
