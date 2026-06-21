# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Doctor: aggregate every stream into one health report and overall verdict."""

from __future__ import annotations

from .falsifier import falsify
from .integrator import integrate
from .model import sha256_obj


def doctor(repo) -> dict:
    integrated = integrate(repo)
    fals = falsify(repo)
    healthy = (
        fals["verdict"] != "FALSIFIED"
        and integrated["protocol_verdict"] == "VALID"
    )
    report = {
        "schema_version": "cmar.doctor/v1",
        "repo": integrated["repo"],
        "readiness_score": integrated["readiness_score"],
        "overall_state": integrated["overall_state"],
        "release_verdict": integrated["release_verdict"],
        "falsification_verdict": fals["verdict"],
        "protocol_verdict": integrated["protocol_verdict"],
        "blocking_voids": integrated["blocking_voids"],
        "root_hash": integrated["root_hash"],
        "healthy": healthy,
    }
    report["doctor_sha256"] = sha256_obj({k: report[k] for k in ("readiness_score", "release_verdict", "falsification_verdict")})
    return report
