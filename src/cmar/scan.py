# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Scan layer: walk a repository into a deterministic mass report by category."""

from __future__ import annotations

from pathlib import Path

from .model import classify, sha256_obj

_IGNORE = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache",
           ".pytest_cache", ".ruff_cache", "dist", "build", ".egg-info"}
CATEGORIES = ("source", "test", "ci", "schema", "security", "docs", "other")


def _iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        parts = set(p.relative_to(root).parts)
        if parts & _IGNORE or any(seg.endswith(".egg-info") for seg in p.parts):
            continue
        yield p


def scan_repo(repo: str | Path) -> dict:
    """Return a deterministic scan report: per-category file counts and byte mass."""
    root = Path(repo).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    mass = dict.fromkeys(CATEGORIES, 0)
    counts = dict.fromkeys(CATEGORIES, 0)
    files: list[dict] = []
    for p in _iter_files(root):
        rel = p.relative_to(root).as_posix()
        cat = classify(rel)
        size = p.stat().st_size
        mass[cat] += size
        counts[cat] += 1
        files.append({"path": rel, "category": cat, "bytes": size})
    total = sum(mass.values())
    report = {
        "schema_version": "cmar.scan/v1",
        "repo": root.name,
        "total_files": len(files),
        "total_mass_bytes": total,
        "mass_by_category": mass,
        "count_by_category": counts,
        "files": files,
        "presence": {
            "ci": counts["ci"] > 0,
            "schema": counts["schema"] > 0,
            "security": counts["security"] > 0,
            "tests": counts["test"] > 0,
            "source": counts["source"] > 0,
        },
    }
    report["scan_sha256"] = sha256_obj({k: v for k, v in report.items() if k != "files"})
    return report
