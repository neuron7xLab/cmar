# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Protocol validation: enforce the invariant 'no evidence, no release'.

A repository may be incomplete and still be protocol-VALID — honesty is the rule,
not completeness. The protocol is INVALID only when the repository *claims*
release (a PASS verdict / a release-marked manifest) while blocking voids remain.
That is the lie the protocol exists to catch.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import sha256_obj
from .voids import build_void_graph


def _claims_release(root: Path) -> bool:
    verdict = root / "RELEASE_VERDICT.md"
    if verdict.is_file():
        text = verdict.read_text(encoding="utf-8", errors="ignore").upper()
        # a bare machine note is fine; an affirmative human PASS is a claim
        if "VERDICT: PASS" in text or "RELEASE: PASS" in text or "STATUS: PASS" in text:
            return True
    manifest = root / "artifacts" / "release_manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if str(data.get("release_verdict", "")).upper() in {"PASS", "RELEASE_READY", "RELEASE"}:
                return True
        except json.JSONDecodeError:
            return False
    return False


def validate_protocol(repo) -> dict:
    root = Path(repo).resolve()
    graph = build_void_graph(repo)
    claims = _claims_release(root)
    violations = []
    if claims and graph["blocking_voids"] > 0:
        violations.append(
            f"claims release while {graph['blocking_voids']} blocking void(s) remain"
        )
    verdict = "INVALID" if violations else "VALID"
    result = {
        "schema_version": "cmar.protocol/v1",
        "claims_release": claims,
        "blocking_voids": graph["blocking_voids"],
        "violations": violations,
        "verdict": verdict,
        "invariant": "no evidence, no release",
    }
    result["protocol_sha256"] = sha256_obj({"v": verdict, "c": claims, "b": graph["blocking_voids"]})
    return result
