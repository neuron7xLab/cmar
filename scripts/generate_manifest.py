#!/usr/bin/env python3
"""Deterministically (re)generate RELEASE_MANIFEST.json from the live repository.

The manifest is NEVER hand-edited; this is its only generator. It reflects
version, status, file_count, total_bytes, command return codes, artifact paths,
and per-file sha256 over the deterministic source tree (generated `artifacts/`
are listed by path only, since their content changes per run).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = dict(os.environ)
ENV["PYTHONPATH"] = str(ROOT / "src")

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", "dist", "build", "node_modules", "artifacts"}


def _version() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    import cmar  # noqa: E402
    return cmar.__version__


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT, env=ENV, text=True, capture_output=True).returncode


def _iter_files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")]
        for fn in fns:
            p = Path(dp) / fn
            rel = p.relative_to(ROOT).as_posix()
            if rel == "RELEASE_MANIFEST.json":
                continue
            yield p, rel


def main() -> int:
    version = _version()
    seed = "examples/seed_14kb_intent"
    commands = {
        "unittest": _run([PY, "-m", "unittest", "discover", "-s", "tests"]),
        "doctor": _run([PY, "-m", "cmar.cli", "doctor"]),
        "integrate": _run([PY, "-m", "cmar.cli", "integrate", seed]),
        "falsify": _run([PY, "-m", "cmar.cli", "falsify", seed]),
        "expand": _run([PY, "-m", "cmar.cli", "expand", seed]),
        "corpus_eval": _run([PY, "-m", "cmar.cli", "corpus-eval",
                             "benchmark_corpus/runtime_v13/artifact_state_stress.jsonl", "--limit", "256"]),
    }

    files = []
    total = 0
    for p, rel in _iter_files():
        try:
            b = p.read_bytes()
        except OSError:
            continue
        files.append({"path": rel, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
        total += len(b)
    files.sort(key=lambda x: x["path"])

    artifacts_dir = ROOT / "artifacts"
    artifact_paths = sorted(
        ("artifacts/" + p.relative_to(artifacts_dir).as_posix())
        for p in artifacts_dir.rglob("*") if p.is_file()
    ) if artifacts_dir.exists() else []

    status = "PASS" if all(rc == 0 for rc in commands.values()) else "FAIL"
    manifest = {
        "name": "cognitive-mass-autofill-runtime",
        "version": version,
        "status": status,
        "generated_by": "scripts/generate_manifest.py",
        "file_count": len(files),
        "total_bytes": total,
        "commands": commands,
        "artifact_paths": artifact_paths,
        "files": files,
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"version": version, "status": status, "file_count": len(files),
                      "total_bytes": total, "commands": commands}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
