from __future__ import annotations
import argparse
import json
from pathlib import Path
from .scanner import scan_repository
from .normalizer import normalize_repository
from .quantizer import quantize_repository
from .voids import build_void_graph
from .planner import build_repair_plan
from .repair import apply_template_repairs
from .protocol import validate_protocol_payload
from .ledger import build_mass_ledger
from .falsifier import falsify_repository
from .autofill import autofill_repository
from .integrator import integrate_artifact_streams
from .runtime import run_runtime_pipeline
from .audit_stream import scan_audit_package, project_audit_to_cmar, integrate_audit_with_cmar
from .corpus_eval import evaluate_corpus
from .report import doctor_markdown
from .github_activity import collect_github_activity

def emit(obj, out=None):
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if isinstance(obj, list):
        obj = [x.to_dict() if hasattr(x, "to_dict") else x for x in obj]
    txt = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(txt + "\n", encoding="utf-8")
    print(txt)
    return 0

def stack(root, target):
    scan = scan_repository(root)
    voids = build_void_graph(scan)
    plan = build_repair_plan(scan, voids)
    ledger = build_mass_ledger(scan, voids, target)
    return scan, voids, plan, ledger

def payload(root, target):
    scan, voids, plan, ledger = stack(root, target)
    return {"scan": scan.to_dict(), "voids": [v.to_dict() for v in voids], "repair_plan": plan.to_dict(), "mass_ledger": ledger.to_dict()}

def c_scan(a): return emit(scan_repository(a.root), a.out)
def c_normalize(a): return emit(normalize_repository(a.root, a.target_valid_mass), a.out)
def c_quantize(a): return emit(quantize_repository(a.root, a.target_valid_mass), a.out)
def c_voids(a): return emit(build_void_graph(scan_repository(a.root)), a.out)
def c_plan(a):
    scan, voids, plan, ledger = stack(a.root, a.target_valid_mass)
    return emit(plan, a.out)
def c_repair(a):
    before = payload(a.root, a.target_valid_mass)
    rr = apply_template_repairs(a.root, getattr(a, "overwrite", False))
    after = payload(a.root, a.target_valid_mass)
    return emit({"repair_result": rr.to_dict(), "before": before["mass_ledger"], "after": after["mass_ledger"]}, a.out)
def c_autofill(a): return emit(autofill_repository(a.root, a.target_valid_mass), a.out)
def c_protocol(a): return emit(validate_protocol_payload(payload(a.root, a.target_valid_mass)), a.out)
def c_falsify(a): return emit(falsify_repository(a.root, a.target_valid_mass), a.out)
def c_integrate(a):
    if getattr(a, "audit_package", None):
        return emit(integrate_audit_with_cmar(a.root, a.audit_package, target_valid_mass=a.target_valid_mass), a.out)
    return emit(integrate_artifact_streams(a.root, a.target_valid_mass, github_activity=getattr(a, "github_activity", None)), a.out)
def c_github_activity(a):
    report = collect_github_activity(a.owner, a.days)
    emit(report, a.out)
    return 0 if report.authenticated else 1
def c_ledger(a):
    scan, voids, plan, ledger = stack(a.root, a.target_valid_mass)
    return emit(ledger, a.out)
def c_runtime(a): return emit(run_runtime_pipeline(a.root, a.target_valid_mass, a.autofill, getattr(a, "github_owner", None), getattr(a, "days", 30)), a.out)
def c_doctor(a):
    scan, voids, plan, ledger = stack(a.root, a.target_valid_mass)
    d = payload(a.root, a.target_valid_mass)
    d["protocol_report"] = validate_protocol_payload(d).to_dict()
    d["normalization_report"] = normalize_repository(a.root, a.target_valid_mass).to_dict()
    d["quantization_report"] = quantize_repository(a.root, a.target_valid_mass).to_dict()
    d["falsification_report"] = falsify_repository(a.root, a.target_valid_mass).to_dict()
    if a.markdown:
        Path(a.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(a.markdown).write_text(doctor_markdown(scan, voids, plan, ledger), encoding="utf-8")
    return emit(d, a.out)

def c_audit_scan(a):
    return emit(scan_audit_package(a.audit_package), a.out)

def c_audit_project(a):
    snap = scan_audit_package(a.audit_package)
    return emit(project_audit_to_cmar(snap), a.out)

def c_audit_fuse(a):
    return emit(integrate_audit_with_cmar(a.root, a.audit_package, target_valid_mass=a.target_valid_mass), a.out)

def c_corpus_eval(a):
    return emit(evaluate_corpus(a.corpus, limit=a.limit), a.out)

def build_parser():
    p = argparse.ArgumentParser(prog="cmar")
    sub = p.add_subparsers(required=True)
    for name, fn in [("scan", c_scan), ("normalize", c_normalize), ("quantize", c_quantize), ("voids", c_voids), ("plan", c_plan), ("repair", c_repair), ("autofill", c_autofill), ("protocol", c_protocol), ("falsify", c_falsify), ("integrate", c_integrate), ("ledger", c_ledger), ("doctor", c_doctor), ("runtime", c_runtime)]:
        sp = sub.add_parser(name)
        if name == "doctor":
            sp.add_argument("root", nargs="?", default=".")
        else:
            sp.add_argument("root")
        sp.add_argument("--out")
        sp.add_argument("--target-valid-mass", type=int, default=1048576)
        if name == "repair": sp.add_argument("--overwrite", action="store_true")
        if name == "doctor": sp.add_argument("--markdown")
        if name == "runtime":
            sp.add_argument("--autofill", action="store_true")
            sp.add_argument("--github-owner")
            sp.add_argument("--days", type=int, default=30)
        if name == "integrate":
            sp.add_argument("--audit-package")
            sp.add_argument("--github-activity")
        sp.set_defaults(func=fn)
    ga = sub.add_parser("github-activity")
    ga.add_argument("owner")
    ga.add_argument("--days", type=int, default=30)
    ga.add_argument("--out")
    ga.set_defaults(func=c_github_activity)
    audit_scan = sub.add_parser("audit-scan")
    audit_scan.add_argument("audit_package")
    audit_scan.add_argument("--out")
    audit_scan.set_defaults(func=c_audit_scan)

    audit_project = sub.add_parser("audit-project")
    audit_project.add_argument("audit_package")
    audit_project.add_argument("--out")
    audit_project.set_defaults(func=c_audit_project)

    audit_fuse = sub.add_parser("audit-fuse")
    audit_fuse.add_argument("root")
    audit_fuse.add_argument("--audit-package", required=True)
    audit_fuse.add_argument("--target-valid-mass", type=int, default=1048576)
    audit_fuse.add_argument("--out")
    audit_fuse.set_defaults(func=c_audit_fuse)

    corpus_eval = sub.add_parser("corpus-eval")
    corpus_eval.add_argument("corpus")
    corpus_eval.add_argument("--limit", type=int, default=256)
    corpus_eval.add_argument("--out")
    corpus_eval.set_defaults(func=c_corpus_eval)

    return p

def _main():
    parser = build_parser()
    a = parser.parse_args()
    return a.func(a)

def main():
    return _main()

if __name__ == "__main__":
    raise SystemExit(_main())
