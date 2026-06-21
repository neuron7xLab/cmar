# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Shared model: deterministic JSON, hashing, file classification, release states."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Discrete release states, ordered weakest -> strongest.
STATES = ("VOID", "WEAK", "PARTIAL", "STRONG", "RELEASE")

# File-category classification by suffix / name. Order matters: first match wins.
_TEST_HINTS = ("test_", "_test.py", "/tests/")
_CI_NAMES = (".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml")
_SECURITY_NAMES = ("security.md", "security.txt")
_DOC_SUFFIXES = (".md", ".rst", ".txt")
_SCHEMA_HINTS = (".schema.json", "/schemas/", "schema.json")
_SOURCE_SUFFIXES = (".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp")


def classify(rel_path: str) -> str:
    """Classify a repository-relative path into a single artifact category."""
    p = rel_path.replace("\\", "/")
    low = p.lower()
    if any(h in low for h in _CI_NAMES):
        return "ci"
    if any(h in low for h in _SCHEMA_HINTS):
        return "schema"
    if any(name == low.rsplit("/", 1)[-1] for name in _SECURITY_NAMES):
        return "security"
    if low.endswith(".py") and (low.rsplit("/", 1)[-1].startswith("test_") or "/tests/" in low):
        return "test"
    if any(low.endswith(s) for s in _SOURCE_SUFFIXES):
        return "source"
    if any(low.endswith(s) for s in _DOC_SUFFIXES):
        return "docs"
    return "other"


def stable_json(obj: object) -> str:
    """Deterministic JSON: sorted keys, fixed separators, trailing newline."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: object) -> str:
    """Hash an object by its canonical JSON — stable across runs."""
    return sha256_text(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def write_json(path: str | Path, obj: object) -> str:
    """Write deterministic JSON to ``path`` (creating parents); return its sha256."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = stable_json(obj)
    p.write_text(text, encoding="utf-8")
    return sha256_text(text)


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else round(float(x), 6)
