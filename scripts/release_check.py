#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CMAR acceptance gate — the single release verdict.

Runs the unit suite, every read-only CLI stream on the seed, and a real autofill
on a throwaway copy, then asserts the machine criteria. Prints exactly one of
``CMAR RELEASE CHECK: PASS`` / ``CMAR RELEASE CHECK: FAIL``.

Invariant: no evidence, no release. A FAIL here means no release, full stop.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "examples" / "seed_14kb_intent"
PY = sys.executable


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, **kw)


def main() -> int:
    failures: list[str] = []

    # 1. unit suite (guard against self-recursion via the env flag)
    env_flag = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "CMAR_IN_RELEASE_CHECK": "1"}
    unit = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests"],
                          cwd=ROOT, env=env_flag, text=True, capture_output=True)
    if unit.returncode != 0:
        failures.append("unit suite failed:\n" + unit.stderr[-2000:])

    # 2. read-only CLI streams on the seed
    for cmd in ("normalize", "quantize", "integrate", "falsify"):
        # map command -> conventional artifact name
        names = {"normalize": "normalized_state.json", "quantize": "quantized_state.json",
                 "integrate": "integrated_state.json", "falsify": "falsification_report.json"}
        target = ROOT / "artifacts" / names[cmd]
        r = _run([PY, "-m", "cmar.cli", cmd, str(SEED), "--out", str(target)])
        if r.returncode != 0:
            failures.append(f"cmar {cmd} returned {r.returncode}: {r.stderr.strip()}")

    # 3. autofill on a disposable copy — must measurably improve the state
    tmp = Path(tempfile.mkdtemp(prefix="cmar_seed_copy_"))
    try:
        copy = tmp / "repo"
        shutil.copytree(SEED, copy)
        rep = _run([PY, "-m", "cmar.cli", "autofill", str(copy),
                    "--out", str(ROOT / "artifacts" / "autofill_report.json")])
        if rep.returncode != 0:
            failures.append(f"cmar autofill returned {rep.returncode}: {rep.stderr.strip()}")
        else:
            import json
            data = json.loads((ROOT / "artifacts" / "autofill_report.json").read_text())
            if not data.get("improved"):
                failures.append("autofill did not improve the state")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 4. doctor report artifact
    _run([PY, "-m", "cmar.cli", "doctor", str(SEED),
          "--out", str(ROOT / "artifacts" / "doctor_report.json")])

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print("CMAR RELEASE CHECK: FAIL")
        return 1
    print("CMAR RELEASE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
