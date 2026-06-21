# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Integration layer: chain the streams so each output feeds the next, one verdict.

scan -> normalize -> quantize -> voids -> plan -> protocol -> ledger -> verdict.
The integrated verdict is emergent: it depends on every upstream stream and the
hash chain over their outputs detects any tampering or drift.
"""

from __future__ import annotations

from .ledger import build_ledger
from .model import sha256_obj
from .normalizer import normalize
from .plan import build_plan
from .protocol import validate_protocol
from .quantizer import quantize
from .scan import scan_repo
from .voids import build_void_graph


def integrate(repo) -> dict:
    scan = scan_repo(repo)
    norm = normalize(repo)
    quant = quantize(repo)
    voids = build_void_graph(repo)
    plan = build_plan(repo)
    protocol = validate_protocol(repo)
    ledger = build_ledger(repo)

    # chain the stream digests: each link carries the previous root
    prev = "0" * 64
    chain = []
    for name, digest in [
        ("scan", scan["scan_sha256"]),
        ("normalized", norm["normalized_sha256"]),
        ("quantized", quant["quantized_sha256"]),
        ("protocol", protocol["protocol_sha256"]),
        ("plan", plan["plan_sha256"]),
        ("ledger", ledger["head_hash"]),
    ]:
        link = sha256_obj({"prev": prev, "stream": name, "digest": digest})
        chain.append({"stream": name, "digest": digest, "link": link})
        prev = link

    # release verdict: RELEASE only when everything lines up
    release_ready = (
        protocol["verdict"] == "VALID"
        and voids["blocking_voids"] == 0
        and ledger["status"] == "OK"
        and quant["overall_state"] in {"STRONG", "RELEASE"}
    )
    verdict = "RELEASE_READY" if release_ready else "BLOCKED"
    return {
        "schema_version": "cmar.integrated/v1",
        "repo": scan["repo"],
        "readiness_score": quant["readiness_score"],
        "overall_state": quant["overall_state"],
        "blocking_voids": voids["blocking_voids"],
        "ledger_status": ledger["status"],
        "protocol_verdict": protocol["verdict"],
        "stream_chain": chain,
        "root_hash": prev,
        "release_verdict": verdict,
    }
