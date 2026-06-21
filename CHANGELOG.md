# Changelog

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
