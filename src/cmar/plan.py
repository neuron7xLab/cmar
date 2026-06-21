# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Repair plan: order the void-graph actions, blocking first, deterministically."""

from __future__ import annotations

from .model import sha256_obj
from .voids import build_void_graph

_PRIORITY = {"test": 0, "ci": 1, "security": 2, "schema": 3, "other": 4, "docs": 5}


def build_plan(repo) -> dict:
    graph = build_void_graph(repo)
    nodes = graph["nodes"]
    # blocking first, then by category priority, then by id (stable)
    ordered = sorted(nodes, key=lambda n: (not n["blocking"], _PRIORITY.get(n["category"], 9), n["id"]))
    steps = [
        {"step": i + 1, "void_id": n["id"], "action": n["action"],
         "target": n["target"], "blocking": n["blocking"]}
        for i, n in enumerate(ordered)
    ]
    plan = {
        "schema_version": "cmar.plan/v1",
        "step_count": len(steps),
        "blocking_steps": sum(1 for s in steps if s["blocking"]),
        "steps": steps,
    }
    plan["plan_sha256"] = sha256_obj(steps)
    return plan
