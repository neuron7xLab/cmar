#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = dict(os.environ)
ENV["PYTHONPATH"] = str(ROOT / "src")

def run(cmd: list[str]):
    return subprocess.run(cmd, cwd=ROOT, env=ENV, text=True, capture_output=True)

def main() -> int:
    audit = ROOT / "data/external_audit_seed/n7x-audit-v4.zip"
    tmp = Path("/tmp/cmar_seed_copy")
    if tmp.exists(): shutil.rmtree(tmp)
    shutil.copytree(ROOT / "examples/seed_14kb_intent", tmp)
    commands = [
        [PY, "-m", "unittest", "discover", "-s", "tests"],
        [PY, "-m", "cmar.cli", "doctor", "--out", "artifacts/doctor_default_root.json"],
        [PY, "-m", "cmar.cli", "normalize", "examples/seed_14kb_intent", "--out", "artifacts/normalized_state.json"],
        [PY, "-m", "cmar.cli", "quantize", "examples/seed_14kb_intent", "--out", "artifacts/quantized_state.json"],
        [PY, "-m", "cmar.cli", "falsify", "examples/seed_14kb_intent", "--out", "artifacts/falsification_report.json"],
        [PY, "-m", "cmar.cli", "integrate", "examples/seed_14kb_intent", "--audit-package", str(audit), "--out", "artifacts/fused_integrated_state.json"],
        [PY, "-m", "cmar.cli", "audit-scan", str(audit), "--out", "artifacts/audit_snapshot.json"],
        [PY, "-m", "cmar.cli", "audit-project", str(audit), "--out", "artifacts/audit_projection.json"],
        [PY, "-m", "cmar.cli", "autofill", str(tmp), "--out", "artifacts/autofill_report.json"],
        [PY, "-m", "cmar.cli", "corpus-eval", "benchmark_corpus/runtime_v13/artifact_state_stress.jsonl", "--limit", "256", "--out", "artifacts/corpus_eval_report.json"],
    ]
    failures=[]
    for cmd in commands:
        r=run(cmd)
        if r.returncode != 0:
            failures.append({"command": cmd, "returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]})
    summary={"commands": len(commands), "failures": failures, "status": "PASS" if not failures else "FAIL"}
    (ROOT/"artifacts/release_check_summary.json").parent.mkdir(parents=True, exist_ok=True)
    (ROOT/"artifacts/release_check_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if failures:
        print("CMAR RELEASE CHECK: FAIL")
        print(json.dumps(failures[0], indent=2))
        return 1
    print("CMAR RELEASE CHECK: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
