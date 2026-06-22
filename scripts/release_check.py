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
        [PY, "-m", "cmar.cli", "expand", "examples/seed_14kb_intent", "--horizon", "5", "--out", "artifacts/expansion_report.json"],
    ]
    failures=[]
    for cmd in commands:
        r=run(cmd)
        if r.returncode != 0:
            failures.append({"command": cmd, "returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]})

    # Future-state gate: project from a clean baseline (capability projection) and
    # assert the system is not diverging and growth is projected.
    exp_env = dict(ENV); exp_env["CMAR_LEDGER_HISTORY"] = "/tmp/cmar_expand_clean_history.jsonl"
    Path("/tmp/cmar_expand_clean_history.jsonl").unlink(missing_ok=True)
    er = subprocess.run([PY, "-m", "cmar.cli", "expand", "examples/seed_14kb_intent", "--out", "/tmp/exp.json"],
                        cwd=ROOT, env=exp_env, text=True, capture_output=True)
    if er.returncode != 0:
        failures.append({"command": "expand-gate", "returncode": er.returncode, "stderr": er.stderr[-2000:]})
    else:
        data = json.loads(Path("/tmp/exp.json").read_text(encoding="utf-8"))
        if data["expansion_verdict"] == "DIVERGING":
            failures.append({"command": "expand-gate", "assert": "system is diverging", "expansion_verdict": data["expansion_verdict"]})
        if not (data["potential_mass"] > data["current"]["valid_mass_bytes"]):
            failures.append({"command": "expand-gate", "assert": "no growth projected",
                             "potential_mass": data["potential_mass"], "current": data["current"]["valid_mass_bytes"]})

    # JSON artifact parse gate: every --out file produced above must parse.
    for cmd in commands:
        if "--out" in cmd:
            out = ROOT / cmd[cmd.index("--out") + 1]
            try:
                json.loads(out.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append({"command": "json-parse", "path": str(out), "error": type(exc).__name__})

    # GitHub-activity fail-closed gate (no live auth): empty PATH removes `gh`.
    fc_env = {"PATH": "/nonexistent", "PYTHONPATH": str(ROOT / "src")}
    fc = subprocess.run([PY, "-m", "cmar.cli", "github-activity", "zzz", "--out", "/tmp/cmar_fc.json"],
                        cwd=ROOT, env=fc_env, text=True, capture_output=True)
    if fc.returncode == 0:
        failures.append({"command": "github-fail-closed", "assert": "must exit non-zero without auth"})
    else:
        try:
            d = json.loads(Path("/tmp/cmar_fc.json").read_text(encoding="utf-8"))
            if d.get("authenticated") is not False or "gh_auth_missing" not in (d.get("collection_errors") or []):
                failures.append({"command": "github-fail-closed", "assert": "expected authenticated=false + gh_auth_missing", "got": d})
        except Exception as exc:
            failures.append({"command": "github-fail-closed", "error": type(exc).__name__})

    # Manifest determinism gate: two regenerations must be byte-identical.
    g1 = run([PY, "scripts/generate_manifest.py"])
    m1 = (ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8") if g1.returncode == 0 else None
    g2 = run([PY, "scripts/generate_manifest.py"])
    m2 = (ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8") if g2.returncode == 0 else None
    if m1 is None or m2 is None or m1 != m2:
        failures.append({"command": "manifest-determinism", "assert": "two regenerations must be identical"})

    # Version-drift gate: package, manifest, and RELEASE_VERDICT must agree.
    try:
        sys.path.insert(0, str(ROOT / "src"))
        import cmar
        pkg_v = cmar.__version__
        man_v = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")).get("version")
        verdict_txt = (ROOT / "RELEASE_VERDICT.md").read_text(encoding="utf-8")
        if man_v != pkg_v:
            failures.append({"command": "version-drift", "package": pkg_v, "manifest": man_v})
        if pkg_v not in verdict_txt:
            failures.append({"command": "version-drift", "assert": f"RELEASE_VERDICT.md must mention {pkg_v}"})
    except Exception as exc:
        failures.append({"command": "version-drift", "error": type(exc).__name__})

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
