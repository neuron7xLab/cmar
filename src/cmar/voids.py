# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Void graph: the set of missing infrastructure that blocks release.

Each void is a node with an id, a category, whether it is release-blocking, and
the autofill action that would resolve it. ``void_pressure`` is the fraction of
declared infrastructure that is absent.
"""

from __future__ import annotations

from .scan import scan_repo

# (void_id, category, blocking, repair_action, target_path)
_REQUIRED = [
    ("no_tests", "test", True, "materialize_tests", "tests/test_smoke.py"),
    ("no_ci", "ci", True, "materialize_ci", ".github/workflows/ci.yml"),
    ("no_schema", "schema", False, "materialize_schema", "schemas/artifact.schema.json"),
    ("no_security", "security", True, "materialize_security", "SECURITY.md"),
    ("no_changelog", "docs", False, "materialize_changelog", "CHANGELOG.md"),
    ("no_release_verdict", "docs", True, "materialize_release_verdict", "RELEASE_VERDICT.md"),
    ("no_release_manifest", "other", True, "materialize_manifest", "artifacts/release_manifest.json"),
    ("no_docs", "docs", False, "materialize_docs", "docs/OVERVIEW.md"),
]


def build_void_graph(repo) -> dict:
    scan = scan_repo(repo)
    counts = scan["count_by_category"]
    from pathlib import Path

    root = Path(repo).resolve()
    present = {f["path"] for f in scan["files"]}

    nodes = []
    for vid, cat, blocking, action, target in _REQUIRED:
        if vid == "no_tests":
            missing = counts["test"] == 0
        elif vid == "no_ci":
            missing = counts["ci"] == 0
        elif vid == "no_schema":
            missing = counts["schema"] == 0
        elif vid == "no_security":
            missing = counts["security"] == 0
        else:
            missing = target not in present and not (root / target).exists()
        if missing:
            nodes.append({"id": vid, "category": cat, "blocking": blocking,
                          "action": action, "target": target})

    blocking = [n for n in nodes if n["blocking"]]
    pressure = round(len(nodes) / len(_REQUIRED), 6)
    return {
        "schema_version": "cmar.voids/v1",
        "void_count": len(nodes),
        "blocking_voids": len(blocking),
        "void_pressure": pressure,
        "nodes": nodes,
    }
