# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Mass ledger: a hash-chained record of valid vs total artifact mass.

Valid mass is mass that carries evidence — source corroborated by tests, plus CI,
schemas, and a security policy. Docs-only mass is NOT valid mass. The ledger
status is BLOCKED unless there is genuine validated mass and tests exist.
"""

from __future__ import annotations

from .model import sha256_obj
from .scan import scan_repo

GENESIS = "0" * 64


def build_ledger(repo) -> dict:
    scan = scan_repo(repo)
    mass = scan["mass_by_category"]
    total = scan["total_mass_bytes"]
    has_tests = scan["count_by_category"]["test"] > 0

    # Valid mass: executable/evidence-bearing categories only when tests exist to
    # corroborate them; docs and 'other' are never valid mass.
    evidence = mass["ci"] + mass["schema"] + mass["security"] + mass["test"]
    corroborated_source = mass["source"] if has_tests else 0
    valid_mass = evidence + corroborated_source
    valid_mass = min(valid_mass, total)  # invariant: valid <= total

    entries = []
    prev = GENESIS
    for cat in sorted(mass):
        payload = {"category": cat, "bytes": mass[cat]}
        h = sha256_obj({"prev": prev, "payload": payload})
        entries.append({**payload, "prev_hash": prev, "record_hash": h})
        prev = h

    status = "OK" if (has_tests and valid_mass > 0 and scan["presence"]["ci"]) else "BLOCKED"
    return {
        "schema_version": "cmar.ledger/v1",
        "total_mass_bytes": total,
        "valid_mass_bytes": valid_mass,
        "valid_mass_ratio": round(valid_mass / total, 6) if total else 0.0,
        "has_tests": has_tests,
        "chain": entries,
        "head_hash": prev,
        "status": status,
    }
