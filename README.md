# CMAR Cognitive Mass Autofill Runtime

Executable runtime for repository state transformation. **Truth is validated by
execution, not by claim** — every metric below is computed by running CMAR
against real repositories, refreshed automatically once a day.

<!-- CMAR-STATS:START -->
### 🛰️ CMAR Truth Stats — validated by execution, not by claim

_Owner `neuron7xLab` (user) · last 30d · generated 2026-06-30T10:03:54.233846+00:00 · source: gh_api + local CMAR scan_

| authored commits | PRs merged/opened | issues closed/opened | contribution days | repos scanned |
|---:|---:|---:|---:|---:|
| **1185** | 558/601 | 30/39 | 24 | 14/14 |

| 🧱 debt (blocking voids) | 🕳️ gaps (falsified repos / findings) | 🔓 critical vulns |
|---:|---:|---:|
| **9** | 2 repos / 9 findings | **n/a** |

<details><summary>Repos needing truth-work</summary>

| repo | status | falsify | debt | crit vulns |
|---|---|---|---:|---:|
| `.github` | FAIL | FALSIFIED | 5 | n/a |
| `neuron7xLab` | FAIL | FALSIFIED | 3 | n/a |
| `Intentia-Amoris` | PARTIAL | NOT_FALSIFIED | 1 | n/a |

</details>

<sub>collection notes: gh_api_failed:user/repos:gh: Resource not accessible by integration (HTTP 403)</sub>
<!-- CMAR-STATS:END -->

## Install

Python 3.10+. Pure stdlib — no third-party runtime dependencies.

```bash
git clone https://github.com/neuron7xLab/cmar
cd cmar
pip install -e .     # exposes the `cmar` CLI
cmar doctor          # sanity-check the install
```

## Quickstart — the core pipeline

Each stage reads an intent seed and writes a machine-readable artifact:

```bash
cmar scan examples/seed_14kb_intent
cmar normalize examples/seed_14kb_intent --out artifacts/normalized_state.json
cmar quantize examples/seed_14kb_intent --out artifacts/quantized_state.json
cmar falsify examples/seed_14kb_intent --out artifacts/falsification_report.json
cmar integrate examples/seed_14kb_intent --out artifacts/integrated_state.json
cmar autofill /tmp/cmar_seed_copy --out artifacts/autofill_report.json
python scripts/release_check.py
```


## Audit stream integration

```bash
cmar audit-scan data/external_audit_seed/n7x-audit-v4.zip --out artifacts/audit_snapshot.json
cmar audit-project data/external_audit_seed/n7x-audit-v4.zip --out artifacts/audit_projection.json
cmar integrate examples/seed_14kb_intent --audit-package data/external_audit_seed/n7x-audit-v4.zip --out artifacts/fused_integrated_state.json
```


## Diagnostics & corpus evaluation

```bash
cmar doctor
cmar corpus-eval benchmark_corpus/runtime_v13/artifact_state_stress.jsonl --limit 256 --out artifacts/corpus_eval_report.json
python scripts/release_check.py
```

`cmar doctor` now defaults to the current directory. The benchmark corpus is now consumed by tests and release check, so it is not dead mass.


## Real GitHub activity evidence

CMAR can collect **real** engineering-activity evidence for a GitHub owner using
the authenticated GitHub CLI. It never fakes private data, never prints or stores
tokens, and fails closed when authentication is missing.

```bash
# 1. Authenticate locally (operator action — credentials never touch the repo)
gh auth status   # or: gh auth login

# 2. Collect real activity (last 30 days)
cmar github-activity neuron7xLab --days 30 --out artifacts/github_activity_30d.json

# 3. Fuse the activity report into the integrated release state (auxiliary evidence)
cmar integrate . --github-activity artifacts/github_activity_30d.json --out artifacts/integrated_state_with_github.json

# 4. One-shot runtime that collects live activity and integrates it
cmar runtime . --github-owner neuron7xLab --days 30 --out artifacts/runtime_real_account.json
```

Allowed authentication sources: the GitHub CLI session, `GITHUB_TOKEN`, or a
fine-grained PAT — **environment only**. If auth is absent, the command returns a
machine-readable error (`{"authenticated": false, "collection_errors": ["gh_auth_missing"]}`)
and a non-zero exit code.

GitHub activity is an **auxiliary** evidence stream. The normalized signals
(`commit_activity_ratio`, `pr_merge_ratio`, `active_days_ratio`,
`repository_activity_ratio`, `github_visibility_signal`) never override repository
quality — the integrated verdict records `github_overrides_quality: false`.


## Cross-stream synthesis

When both the repository-quality stream and the GitHub-activity stream are
present, `integrate`/`runtime` emit an **emergent** `cross_stream_synthesis`
state that no single module can produce alone:

- `convergence_state` ∈ {`CONVERGENT_MATURE`, `ACTIVITY_WITHOUT_STRUCTURE`,
  `STRUCTURE_WITHOUT_ACTIVITY`, `IMMATURE_BOTH_STREAMS`}
- `stream_coherence` — how strongly structure and activity agree (1.0 = full agreement)
- `activity_theater_suspected` — high activity masking weak structure

It is descriptive: `overrides_quality: false` — activity never raises the gate.


## HTTP runtime server

Move CMAR from dev CLI to a running service external agents can call:

```bash
cmar serve . --host 127.0.0.1 --port 8787
# GET /health  /version  /runtime  /integrate  /github-activity?owner=<login>&days=30
curl -s http://127.0.0.1:8787/health
curl -s "http://127.0.0.1:8787/runtime"
```

Zero-dependency (stdlib only), read-only, fixed root, fail-closed, never returns
tokens. Binds to localhost by default; put it behind an authenticating proxy
before exposing publicly (it shares the server's GitHub read scope).


## Future-state projection

CMAR projects where the artifact is heading, not just where it is:

```bash
cmar expand examples/seed_14kb_intent --horizon 5 --out artifacts/expansion_report.json
```

Output: `potential_mass` (computed N iterations ahead), `velocity`
(valid-mass and void-closure per iteration), `projected_states`, a deterministic
`entropy_estimate` = `blocking_voids / (voids_detected + 1)`, and an
`expansion_verdict` ∈ {`CONVERGING`, `STABLE`, `DIVERGING`} derived from velocity
signs. With no history it uses a conservative baseline (`confidence: LOW`);
`cmar ledger` appends snapshots to `artifacts/ledger_history.jsonl`
(override path via `CMAR_LEDGER_HISTORY`), so velocity becomes measured after 2+
runs. `integrate` embeds `expansion` / `potential_mass` / `expansion_verdict`.

Falsifier invariant **F11** (`expansion_not_diverging_on_release`): a release
must not pass while the system is projected to degrade.

## License

[MIT](LICENSE) © 2023–2026 Yaroslav Vasylenko (neuron7xLab)
