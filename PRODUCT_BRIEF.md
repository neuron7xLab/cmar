# CMAR Product Brief v1.4.1

CMAR is a repository-state control runtime for AI-assisted software materialization.

It does not replace tests, CI, security policy, schemas, or release evidence. It measures whether those layers exist, turns absence into typed blockers, and produces a deterministic JSON verdict.

## Problem

AI-assisted repositories often contain convincing prose, scaffold files, and partial code, but lack executable evidence. Human review then becomes slow and subjective.

## Product function

CMAR converts repository state into a machine-verifiable artifact state:

```text
what exists -> what is missing -> what blocks release -> what must be built -> whether the result survives falsification
```

## Current product level

Push-ready open-source runtime seed. It is not a mature SaaS. It is a CLI-first engineering instrument with tests, JSON artifacts, release gate, and external audit-stream fusion.
