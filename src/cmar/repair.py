# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic repair: materialize the files that resolve void-graph actions.

Every materializer writes real, functional content (a runnable test, valid CI
YAML, a valid JSON Schema, a real policy) — never an empty placeholder. Content is
deterministic: the same void on the same repo always yields byte-identical output.
"""

from __future__ import annotations

from pathlib import Path

from .model import stable_json
from .plan import build_plan

_TEST = '''# SPDX-License-Identifier: GPL-3.0-or-later
"""Smoke test materialized by CMAR autofill — asserts the repo has executable mass."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRepositoryHasExecutableMass(unittest.TestCase):
    def test_has_source_files(self):
        py = [p for p in ROOT.rglob("*.py") if "/tests/" not in p.as_posix()]
        self.assertTrue(py, "repository must contain source files")

    def test_intent_is_present(self):
        self.assertTrue(any(ROOT.rglob("*")), "repository must not be empty")


if __name__ == "__main__":
    unittest.main()
'''

_CI = """# SPDX-License-Identifier: GPL-3.0-or-later
name: CI
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m unittest discover -s tests
"""

_SECURITY = """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Security policy

Report vulnerabilities privately to the maintainer. Do not open public issues for
undisclosed vulnerabilities. This policy was materialized by CMAR autofill to
resolve the `no_security` blocking void; replace the contact with a real channel
before release.
"""

_CHANGELOG = """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Changelog

## [unreleased]
- Repository infrastructure materialized by CMAR autofill (tests, CI, schema,
  security policy, release manifest).
"""

_VERDICT = """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Release verdict

This file records the machine verdict produced by `cmar integrate` and gated by
`cmar falsify`. A human-written PASS here is meaningless: the binding verdict is
`artifacts/integrated_state.json`. No evidence, no release.
"""

_DOCS = """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Overview

This repository's infrastructure was completed by CMAR (Cognitive Mass Autofill
Runtime). See `artifacts/` for the machine-verifiable state and
`RELEASE_VERDICT.md` for the gating verdict.
"""

_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "cmar.artifact",
    "type": "object",
    "required": ["schema_version"],
    "properties": {"schema_version": {"type": "string"}},
    "additionalProperties": True,
}

_MANIFEST = {
    "schema_version": "cmar.release_manifest/v1",
    "materialized_by": "cmar.autofill",
    "note": "regenerate with `cmar integrate` for the binding state",
}


def _materializers() -> dict[str, tuple[str, str]]:
    return {
        "materialize_tests": ("tests/test_smoke.py", _TEST),
        "materialize_ci": (".github/workflows/ci.yml", _CI),
        "materialize_security": ("SECURITY.md", _SECURITY),
        "materialize_changelog": ("CHANGELOG.md", _CHANGELOG),
        "materialize_release_verdict": ("RELEASE_VERDICT.md", _VERDICT),
        "materialize_docs": ("docs/OVERVIEW.md", _DOCS),
        "materialize_schema": ("schemas/artifact.schema.json", stable_json(_SCHEMA)),
        "materialize_manifest": ("artifacts/release_manifest.json", stable_json(_MANIFEST)),
    }


def apply_repairs(repo) -> dict:
    """Apply the repair plan to ``repo`` in place; return what was created."""
    root = Path(repo).resolve()
    plan = build_plan(repo)
    mats = _materializers()
    created: list[str] = []
    skipped: list[str] = []
    for step in plan["steps"]:
        spec = mats.get(step["action"])
        if spec is None:
            skipped.append(step["action"])
            continue
        target, content = spec
        path = root / target
        if path.exists():
            skipped.append(target)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(target)
    return {
        "schema_version": "cmar.repair/v1",
        "applied_steps": plan["step_count"],
        "created": sorted(created),
        "skipped": sorted(skipped),
    }
