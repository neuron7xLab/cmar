# Changelog

## 1.9.0

- Added `cmar stats <owner>` and `src/cmar/stats.py`: computes **real** owner truth-metrics across public repos — authored GitHub activity, debt (blocking voids), gaps (falsification verdicts/findings), and critical Dependabot vulnerabilities — by cloning + running CMAR each run. Fail-closed; unavailable data is `null`/`n/a`, never faked.
- Added `scripts/update_readme_stats.py` + a `<!-- CMAR-STATS:START/END -->` block in `README.md`: a live, self-updating truth dashboard.
- Added `.github/workflows/daily-stats.yml`: refreshes the README dashboard once a day (cron) and on demand; uses `CMAR_PAT` secret if present (private repos + cross-repo vuln data), else the scoped token.
- Added `tests/test_stats.py` (67 tests total).

## 1.8.1

- GitHub activity now detects **owner type** (`user` / `organization` / `unknown`) via `gh api users/<owner>` and scopes search queries accordingly: organizations use `org:<owner>`, **user accounts use `author:<owner>`** (previously `org:` was used for all owners, which mislabeled repo-commits as authored commits for user accounts). Added `owner_type` to the report schema. Real check: `neuron7xLab` is a User → `commits_authored` now counts authored commits, not all repo commits.
- Defensive token redaction: any token-like string in captured `gh` stderr is replaced with `[REDACTED]` before entering `collection_errors`/artifacts.
- Hardened `release_check.py`: added JSON-parse gate, GitHub fail-closed gate (no-auth → non-zero + `gh_auth_missing`), manifest-determinism gate, and version-drift gate (package == manifest == RELEASE_VERDICT).
- CI matrix across Python 3.10 / 3.11 / 3.12; live GitHub not required (fail-closed tested via mocks).
- Added `tests/test_github_activity_user_owner.py`, `_org_owner.py`, `_fail_closed.py`, `_no_token_leak.py`; added `docs/OPERATOR_RUNBOOK.md`.
- Stopped tracking generated `artifacts/*.json|jsonl` (regenerated proof only).

## 1.8.0

- Added an empirical validity study of the expansion projector (`studies/expansion_validity/`): 4 real measured trajectories, OLS vs two-endpoint, forecast error vs the 0.15 criterion, falsification test of `expansion_verdict`. Verdict: directionally predictive (not falsified); magnitude reliable only under local linearity. See `studies/expansion_validity/REPORT.md`.
- Evidence-driven expander upgrade: velocity now estimated by **OLS** over the full series (beats two-endpoint under noise); `confidence` is gated on fit quality (`LOW` <3 pts / `MEDIUM` R²<0.9 / `HIGH` R²≥0.9) instead of point count; added `model`, `fit_quality`, and a `nonlinearity_warning` that flags when `potential_mass` magnitude is unreliable on non-linear trajectories.

## 1.7.0

- Added future-state projector (`src/cmar/expander.py`): `compute_expansion(ledger, history, horizon)` computes `potential_mass`, an `expansion_vector` (velocity), `projected_states`, a deterministic `entropy_estimate` (`blocking_voids / (voids_detected + 1)`), and an `expansion_verdict` (`CONVERGING` / `STABLE` / `DIVERGING`) derived from velocity signs. Empty history → conservative baseline marked `confidence: LOW`.
- Added `cmar expand <repo> [--horizon N] [--out]`.
- Wired expansion into `integrate`: `integrated_state` now carries `expansion`, `potential_mass`, `expansion_verdict`.
- Added ledger-history persistence: `cmar ledger` appends a snapshot to `artifacts/ledger_history.jsonl` (path overridable via `CMAR_LEDGER_HISTORY`), so velocity becomes measured after 2+ runs.
- Added falsifier invariant F11 `expansion_not_diverging_on_release` (`RELEASE_WHILE_DIVERGING`, high): release must not pass while the system is projected to degrade.
- Extended `release_check.py` with a future-state gate (not diverging + growth projected from a clean baseline).
- Added `tests/test_expander.py` (47 tests total).

## 1.6.0

- Added cross-stream synthesis (`src/cmar/synthesis.py`): joins the repository-quality stream and the GitHub-activity stream into an emergent convergence state (`CONVERGENT_MATURE` / `ACTIVITY_WITHOUT_STRUCTURE` / `STRUCTURE_WITHOUT_ACTIVITY` / `IMMATURE_BOTH_STREAMS`) with a `stream_coherence` scalar and an `activity_theater_suspected` cross-stream finding. Descriptive only — never overrides the release gate.
- Wired synthesis into `integrate`/`runtime` (`cross_stream_synthesis` field) when a GitHub stream is present.
- Recalibrated `commit_activity_ratio` to the heavy-tailed GitHub distribution: soft saturation `cpd/(cpd+k)` (k=3.0) preserves the origin slope (low/normal behavior unchanged) and removes the hard clamp that destroyed ordering on very active accounts.
- Added `cmar serve` — a zero-dependency stdlib HTTP runtime server (`/health`, `/version`, `/runtime`, `/integrate`, `/github-activity`) for external agents; read-only, fixed root, fail-closed, never returns tokens.
- Added `tests/test_synthesis.py` and `tests/test_server.py` (39 tests total).

## 1.5.0

- Added real GitHub activity runtime (`src/cmar/github_activity.py`) using the authenticated `gh` CLI; fails closed on missing auth, never prints or stores tokens, accumulates partial API failures in `collection_errors`.
- Added `cmar github-activity <owner> --days N --out ...` command.
- Integrated GitHub activity as an auxiliary evidence stream: `cmar integrate . --github-activity <file>` and `cmar runtime . --github-owner <owner> --days N`.
- Added normalized GitHub signals (`commit_activity_ratio`, `pr_merge_ratio`, `active_days_ratio`, `repository_activity_ratio`, `github_visibility_signal`); they never override repository quality (`github_overrides_quality: false`).
- Added offline, mock-based tests `tests/test_github_activity.py` and `tests/test_runtime_real_account.py` (no live network dependency).

## 1.4.1

- Fixed `cmar doctor` so it defaults to the current directory when no root is provided.
- Replaced runtime placeholder chapters with operational module documentation.
- Added `src/cmar/corpus_eval.py`.
- Added `cmar corpus-eval` command.
- Added tests proving `cmar doctor` default execution and benchmark corpus consumption.
- Extended release gate to run doctor default and corpus evaluation.
- Updated release manifest after regenerated artifacts.

# Changelog

## 1.4.1

- Integrated n7x-audit-v4.zip as an external audit stream.
- Added audit package scanner, symbol extractor, capability projector, and fusion verdict.
- Added CLI: audit-scan, audit-project, audit-fuse.
- Extended integrate with --audit-package.
- Added stream-linkage artifacts and tests.

# Changelog

## 1.4.1

- Added cognitive runtime modules, CLI surface, tests, artifacts, release gate, stress corpus.
