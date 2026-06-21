from __future__ import annotations
import json

def to_json(obj):
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if isinstance(obj, list):
        obj = [x.to_dict() if hasattr(x, "to_dict") else x for x in obj]
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

def doctor_markdown(scan, voids, plan, ledger):
    lines = [
        "# CMAR Doctor Report",
        "",
        f"- artifact_hash: `{scan.artifact_hash}`",
        f"- total_files: {scan.total_files}",
        f"- total_bytes: {scan.total_bytes}",
        f"- status: {ledger.status}",
        "",
        "## Voids",
    ]
    lines += [f"- {v.void_id}: {v.title}" for v in voids] or ["- none"]
    return "\n".join(lines) + "\n"
