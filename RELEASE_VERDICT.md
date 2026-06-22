# CMAR Release Verdict

## Version

1.9.0

## Status

```text
FINAL_PUSH_READY
GITHUB_ACTIVITY_RUNTIME_LIVE
CROSS_STREAM_SYNTHESIS_EMERGENT
HTTP_RUNTIME_SERVER_DEPLOYABLE
FUTURE_STATE_EXPANSION_PROJECTOR
EXPANSION_VALIDITY_STUDIED_AND_EVIDENCE_DRIVEN
CORPUS_WIRED_TO_TESTS_AND_RELEASE_GATE
```

## Machine Gates

```text
python -m unittest discover -s tests          # 52 tests, 0 failures
python scripts/release_check.py                # CMAR RELEASE CHECK: PASS
cmar integrate examples/seed_14kb_intent       # rc 0, carries potential_mass
cmar falsify   examples/seed_14kb_intent       # rc 0
cmar expand    examples/seed_14kb_intent       # rc 0, expansion_verdict
cmar github-activity neuron7xLab --days 30     # rc 0 when authenticated, else fail-closed
cmar corpus-eval benchmark_corpus/runtime_v13/artifact_state_stress.jsonl --limit 256
```

## Verdict

CMAR v1.8.0 is push-ready. The runtime scans, normalizes, quantizes, detects
voids, plans repairs, validates protocol, falsifies invalid claims (incl. F11
`expansion_not_diverging_on_release`), autofills missing structure, collects real
GitHub activity (fail-closed, token-redacting), synthesizes an emergent
cross-stream convergence state, projects future state with an OLS / R²-gated
expansion projector, and serves the runtime over HTTP for external agents. Every
module consumes another module's output and emits deterministic JSON. The
expansion projector's predictive validity is empirically studied in
`studies/expansion_validity/` (directionally predictive; magnitude reliable only
under local linearity, with an explicit `nonlinearity_warning`).
