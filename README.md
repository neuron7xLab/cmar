<!-- SPDX-License-Identifier: CC-BY-4.0 -->

```text
 ██████ ███    ███  █████  ██████
██      ████  ████ ██   ██ ██   ██
██      ██ ████ ██ ███████ ██████
██      ██  ██  ██ ██   ██ ██   ██
 ██████ ██      ██ ██   ██ ██   ██
```

# CMAR — Cognitive Mass Autofill Runtime

**Turns raw software intent into a validated, falsification-gated artifact state.**

CMAR does not describe quality — it *measures* it, *materializes* what is missing,
and *refuses to lie* about the result. It is a deterministic pipeline of
independent streams, each chained into the next, ending in a machine verdict.

```text
intent → scan → normalize → quantize → void graph → repair plan
       → deterministic repair → protocol validation → integration
       → mass ledger → release verdict
```

## Invariant

```text
No evidence, no release.
No validated capability, no product.
No protocol verdict, no completion.
```

## Quickstart

```bash
python -m pip install -e .
python scripts/release_check.py                 # CMAR RELEASE CHECK: PASS
cmar integrate examples/seed_14kb_intent        # BLOCKED — the seed is honestly incomplete
cmar falsify   examples/seed_14kb_intent        # PARTIAL — weak, but not a lie
cp -r examples/seed_14kb_intent /tmp/copy && cmar autofill /tmp/copy   # improved: true
```

## What each command does

`scan` · `normalize` · `quantize` · `voids` · `plan` · `repair` · `autofill` ·
`protocol` · `integrate` · `falsify` · `ledger` · `doctor` — 12 deterministic,
JSON-emitting streams (`--out`, returncode 0 on valid input). See [docs/CLI.md](docs/CLI.md).

## Why it cannot lie

- **Protocol** marks a repo `INVALID` only when it *claims* release while blocking
  voids remain — the one lie CMAR exists to catch ([docs/INVARIANT.md](docs/INVARIANT.md)).
- **Ledger** enforces `valid_mass ≤ total_mass` over a hash chain; docs-only mass
  is never valid mass.
- **Falsifier** actively tries to refute the state before any release verdict
  ([docs/FALSIFICATION.md](docs/FALSIFICATION.md)).
- **Autofill** proves completion by a measured before/after delta, not a claim
  ([docs/AUTOFILL.md](docs/AUTOFILL.md)).
- **Release gate** (`scripts/release_check.py`) is the single source of the verdict.

## Layout

```text
src/cmar/        14 runtime modules
tests/           14 unittest modules
examples/        seed intent the runtime operates on
schemas/         5 artifact JSON schemas
docs/            8 documents
artifacts/       generated machine state
scripts/         release_check.py — the acceptance gate
```

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
Pipeline: [docs/PIPELINE.md](docs/PIPELINE.md) ·
Demo: [docs/DEMO.md](docs/DEMO.md). Licensed GPL-3.0-or-later (code), CC-BY-4.0 (docs).
