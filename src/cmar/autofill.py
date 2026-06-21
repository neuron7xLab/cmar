from __future__ import annotations
from pathlib import Path
from .models import AutofillReport
from .scanner import scan_repository
from .voids import build_void_graph
from .ledger import build_mass_ledger
from .repair import apply_template_repairs

def _snap(root, target):
    scan = scan_repository(root)
    voids = build_void_graph(scan)
    ledger = build_mass_ledger(scan, voids, target)
    return {"scan": scan.to_dict(), "mass_ledger": ledger.to_dict()}

def _w(root, rel, txt, created, skipped):
    p = root / rel
    if p.exists():
        skipped.append(rel)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    created.append(rel)

def autofill_repository(root, target_valid_mass=1048576):
    root = Path(root).resolve()
    before = _snap(root, target_valid_mass)
    rr = apply_template_repairs(root)
    created = list(rr.created_files)
    skipped = list(rr.skipped_files)
    _w(root, "docs/runtime_pipeline.md", "# Runtime Pipeline\n\nscan -> normalize -> quantize -> voids -> plan -> protocol -> falsify -> ledger -> verdict\n", created, skipped)
    _w(root, "artifacts/.gitkeep", "", created, skipped)
    _w(root, "schemas/runtime_state.schema.json", '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","required":["status"]}\n', created, skipped)
    after = _snap(root, target_valid_mass)
    bl = before["mass_ledger"]
    al = after["mass_ledger"]
    acceptance = {
        "valid_mass_increased": al["valid_mass_bytes"] > bl["valid_mass_bytes"],
        "blocking_voids_not_increased": al["blocking_voids"] <= bl["blocking_voids"],
        "total_files_increased": after["scan"]["total_files"] > before["scan"]["total_files"],
    }
    return AutofillReport("cmar-autofill/1.4.1", str(root), sorted(set(created)), sorted(set(skipped)), bl, al, all(acceptance.values()), acceptance)
