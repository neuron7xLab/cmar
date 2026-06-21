from __future__ import annotations

import ast
import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditFileRecord:
    path: str
    bytes: int
    sha256: str
    layer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditPackageSnapshot:
    audit_stream_version: str
    package_path: str
    package_hash: str
    total_files: int
    total_bytes: int
    layer_files: dict[str, int]
    layer_bytes: dict[str, int]
    python_modules: list[str]
    test_files: list[str]
    workflow_files: list[str]
    cli_files: list[str]
    declared_commands: list[str]
    exported_symbols: dict[str, list[str]]
    files: list[AuditFileRecord]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["files"] = [f.to_dict() for f in self.files]
        return d


@dataclass(frozen=True)
class AuditProjection:
    projection_version: str
    source_package_hash: str
    capability_vector: dict[str, float]
    accepted_capabilities: list[str]
    rejected_capabilities: list[str]
    projection_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditFusionReport:
    fusion_version: str
    cmar_root: str
    audit_package: str
    stream_linkage: list[dict[str, str]]
    cmar_integrated_state: dict[str, Any]
    audit_snapshot: dict[str, Any]
    audit_projection: dict[str, Any]
    fused_verdict: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _layer(path: str) -> str:
    p = path.lower()
    name = Path(path).name.lower()
    if "/tests/" in "/" + p or name.startswith("test_"):
        return "test"
    if ".github/workflows" in p or name.endswith(".yml") and "workflow" in p:
        return "ci"
    if "/pipeline/" in p or name in {"normalizer.py", "quantizer.py", "integrator.py", "falsifier.py", "projector.py"}:
        return "pipeline"
    if "/scorers/" in p:
        return "scorer"
    if "/collectors/" in p:
        return "collector"
    if "/renderers/" in p:
        return "renderer"
    if name in {"pyproject.toml", "run.py"}:
        return "entrypoint"
    if name.endswith(".py"):
        return "source"
    if name.endswith((".md", ".txt", ".rst")):
        return "docs"
    return "other"


def _parse_symbols(path: str, data: bytes) -> list[str]:
    if not path.endswith(".py"):
        return []
    try:
        tree = ast.parse(data.decode("utf-8"), filename=path)
    except Exception:
        return []
    symbols: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    return symbols


def _parse_commands(path: str, data: bytes) -> list[str]:
    if not path.endswith(".py"):
        return []
    text = data.decode("utf-8", errors="ignore")
    commands: set[str] = set()
    for marker in ["add_parser(", "@app.command", "subcommands"]:
        if marker in text:
            break
    # Conservative regex for argparse subcommand names.
    for match in __import__("re").finditer(r"add_parser\(['\"]([^'\"]+)['\"]", text):
        commands.add(match.group(1))
    # Fallback: top-level command-like function names.
    for match in __import__("re").finditer(r"def\s+(cmd_[a-zA-Z0-9_]+|c_[a-zA-Z0-9_]+)\s*\(", text):
        commands.add(match.group(1))
    return sorted(commands)


def scan_audit_package(path: str | Path) -> AuditPackageSnapshot:
    package = Path(path).resolve()
    data = package.read_bytes()
    records: list[AuditFileRecord] = []
    exported: dict[str, list[str]] = {}
    commands: set[str] = set()
    layer_files: dict[str, int] = {}
    layer_bytes: dict[str, int] = {}
    python_modules: list[str] = []
    test_files: list[str] = []
    workflow_files: list[str] = []
    cli_files: list[str] = []

    with zipfile.ZipFile(package) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if info.is_dir():
                continue
            blob = z.read(info.filename)
            layer = _layer(info.filename)
            rec = AuditFileRecord(info.filename, len(blob), _sha(blob), layer)
            records.append(rec)
            layer_files[layer] = layer_files.get(layer, 0) + 1
            layer_bytes[layer] = layer_bytes.get(layer, 0) + len(blob)
            if info.filename.endswith(".py"):
                python_modules.append(info.filename)
                exported[info.filename] = _parse_symbols(info.filename, blob)
                for cmd in _parse_commands(info.filename, blob):
                    commands.add(cmd)
            if layer == "test":
                test_files.append(info.filename)
            if layer == "ci":
                workflow_files.append(info.filename)
            if Path(info.filename).name == "cli.py" or Path(info.filename).name == "run.py":
                cli_files.append(info.filename)

    return AuditPackageSnapshot(
        audit_stream_version="cmar-audit-stream/1.4.1",
        package_path=str(package),
        package_hash=_sha(data),
        total_files=len(records),
        total_bytes=sum(r.bytes for r in records),
        layer_files=dict(sorted(layer_files.items())),
        layer_bytes=dict(sorted(layer_bytes.items())),
        python_modules=python_modules,
        test_files=test_files,
        workflow_files=workflow_files,
        cli_files=cli_files,
        declared_commands=sorted(commands),
        exported_symbols=exported,
        files=records,
    )


def project_audit_to_cmar(snapshot: AuditPackageSnapshot) -> AuditProjection:
    lf = snapshot.layer_files
    exported_names = {name for names in snapshot.exported_symbols.values() for name in names}

    required = {
        "normalizer": any("normalizer.py" in m for m in snapshot.python_modules) or "normalize" in " ".join(exported_names).lower(),
        "quantizer": any("quantizer.py" in m for m in snapshot.python_modules) or "quantize" in " ".join(exported_names).lower(),
        "integrator": any("integrator.py" in m for m in snapshot.python_modules) or "integrate" in " ".join(exported_names).lower(),
        "falsifier": any("falsifier.py" in m for m in snapshot.python_modules) or "falsify" in " ".join(exported_names).lower(),
        "scorers": lf.get("scorer", 0) > 0,
        "collectors": lf.get("collector", 0) > 0,
        "tests": lf.get("test", 0) > 0,
        "ci": lf.get("ci", 0) > 0,
        "cli": bool(snapshot.cli_files),
    }
    vector = {k: 1.0 if v else 0.0 for k, v in required.items()}
    accepted = sorted(k for k, v in required.items() if v)
    rejected = sorted(k for k, v in required.items() if not v)
    score = sum(vector.values()) / max(len(vector), 1)
    verdict = "AUDIT_STREAM_ACCEPTED" if score >= 0.80 else ("AUDIT_STREAM_PARTIAL" if score >= 0.50 else "AUDIT_STREAM_REJECTED")
    return AuditProjection(
        projection_version="cmar-audit-projection/1.4.1",
        source_package_hash=snapshot.package_hash,
        capability_vector=vector,
        accepted_capabilities=accepted,
        rejected_capabilities=rejected,
        projection_verdict=verdict,
    )


def integrate_audit_with_cmar(root: str | Path, audit_package: str | Path, *, target_valid_mass: int = 1_048_576) -> AuditFusionReport:
    from .integrator import integrate_artifact_streams

    cmar_state = integrate_artifact_streams(root, target_valid_mass=target_valid_mass)
    snapshot = scan_audit_package(audit_package)
    projection = project_audit_to_cmar(snapshot)

    cmar_gate = cmar_state.integrated_verdict.get("gate")
    if projection.projection_verdict == "AUDIT_STREAM_ACCEPTED":
        audit_gate = "PASS_AUDIT_STREAM"
    elif projection.projection_verdict == "AUDIT_STREAM_PARTIAL":
        audit_gate = "PARTIAL_AUDIT_STREAM"
    else:
        audit_gate = "FAIL_AUDIT_STREAM"

    if cmar_gate == "PASS" and audit_gate == "PASS_AUDIT_STREAM":
        state = "FUSED_RELEASE_CANDIDATE"
        gate = "PASS"
    elif audit_gate == "FAIL_AUDIT_STREAM":
        state = "FUSION_REJECTED"
        gate = "FAIL_AUDIT_STREAM"
    else:
        state = "FUSED_PARTIAL_OPERATIONAL_STATE"
        gate = "CONTINUE_INTEGRATION"

    linkage = [
        {"from": "cmar.scan.output", "to": "cmar.normalizer.input"},
        {"from": "cmar.normalizer.output", "to": "cmar.quantizer.input"},
        {"from": "cmar.quantizer.output", "to": "cmar.void_graph.input"},
        {"from": "cmar.void_graph.output", "to": "cmar.repair_plan.input"},
        {"from": "cmar.repair_plan.output", "to": "cmar.protocol.input"},
        {"from": "cmar.protocol.output", "to": "cmar.falsifier.input"},
        {"from": "n7x.audit_zip", "to": "audit_stream.scan.input"},
        {"from": "audit_stream.scan.output", "to": "audit_projection.input"},
        {"from": "audit_projection.output", "to": "fusion_verdict.input"},
        {"from": "cmar.integrated_verdict.output", "to": "fusion_verdict.input"},
    ]

    return AuditFusionReport(
        fusion_version="cmar-audit-fusion/1.4.1",
        cmar_root=str(Path(root).resolve()),
        audit_package=str(Path(audit_package).resolve()),
        stream_linkage=linkage,
        cmar_integrated_state=cmar_state.to_dict(),
        audit_snapshot=snapshot.to_dict(),
        audit_projection=projection.to_dict(),
        fused_verdict={
            "state": state,
            "gate": gate,
            "cmar_gate": cmar_gate,
            "audit_gate": audit_gate,
            "reason": "CMAR runtime stream and N7X audit package stream were projected into one fused verdict.",
        },
    )


def write_json(path: str | Path, obj: Any) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
