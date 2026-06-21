from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .falsifier import falsify_payload
from .normalizer import normalize_payload
from .quantizer import quantize_artifact_state


@dataclass(frozen=True)
class CorpusEvalReport:
    evaluator_version: str
    corpus_path: str
    records: int
    expected_blocked_accuracy: float
    quantized_distribution: dict[str, int]
    falsification_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _payload_from_record(record: dict[str, Any]) -> dict[str, Any]:
    artifact_hash = record.get("artifact_hash", "")
    missing = record.get("missing_surface", [])
    total = int(record.get("total_bytes", 0))
    valid = int(record.get("valid_mass_bytes", 0))
    scan = {
        "artifact_hash": artifact_hash,
        "total_bytes": total,
        "layer_bytes": record.get("layer_bytes", {}),
        "missing_surface": missing,
        "risk_flags": [],
    }
    ledger = {
        "artifact_hash": artifact_hash,
        "total_bytes": total,
        "valid_mass_bytes": valid,
        "target_valid_mass_bytes": 1_048_576,
        "voids_detected": len(missing),
        "blocking_voids": sum(1 for x in missing if x in {"tests", "ci", "entrypoint"}),
        "release_blocked": bool({"tests", "ci", "entrypoint"} & set(missing)),
        "status": "BLOCKED" if bool({"tests", "ci", "entrypoint"} & set(missing)) else "PASS",
    }
    return {"scan": scan, "mass_ledger": ledger, "protocol_report": {"valid": True}}


def evaluate_corpus(path: str | Path, *, limit: int = 256) -> CorpusEvalReport:
    path = Path(path)
    qdist: dict[str, int] = {}
    fdist: dict[str, int] = {}
    correct = 0
    n = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            payload = _payload_from_record(record)
            quant = quantize_artifact_state(payload)
            payload["quantization_report"] = quant.to_dict()
            fals = falsify_payload(payload)
            qdist[quant.verdict] = qdist.get(quant.verdict, 0) + 1
            fdist[fals.verdict] = fdist.get(fals.verdict, 0) + 1
            expected = bool(record.get("expected_blocked", False))
            predicted = fals.verdict == "FALSIFIED"
            correct += int(expected == predicted)
            n += 1
            if n >= limit:
                break
    return CorpusEvalReport(
        evaluator_version="cmar-corpus-eval/1.4.1",
        corpus_path=str(path),
        records=n,
        expected_blocked_accuracy=round(correct / max(n, 1), 6),
        quantized_distribution=dict(sorted(qdist.items())),
        falsification_distribution=dict(sorted(fdist.items())),
    )
