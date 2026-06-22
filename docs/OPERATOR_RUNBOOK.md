# CMAR Operator Runbook

Practical daily usage for running CMAR against `neuron7xLab` repositories and
GitHub activity. No theory — just commands and what their results mean.

## Install and verify

```bash
git clone https://github.com/neuron7xLab/cmar.git
cd cmar
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests
python scripts/release_check.py
```

`release_check.py` must print exactly one terminal line: `CMAR RELEASE CHECK: PASS`.

## Real GitHub activity

```bash
gh auth status   # must show a logged-in account; otherwise: gh auth login
cmar github-activity neuron7xLab --days 30 --out artifacts/github_activity_30d.json
cmar runtime . --github-owner neuron7xLab --days 30 --out artifacts/runtime_real_account.json
```

The collector auto-detects whether the owner is a **user** or an
**organization** (`owner_type` field) and scopes its queries accordingly
(`author:` for users, `org:` for organizations). Tokens are never printed or
written; any token-like text in errors is `[REDACTED]`.

## Serve the runtime to external agents

```bash
cmar serve . --host 127.0.0.1 --port 8787
curl -s http://127.0.0.1:8787/health
curl -s "http://127.0.0.1:8787/github-activity?owner=neuron7xLab&days=30"
```

Binds to localhost by default. Exposing publicly shares the server's GitHub read
scope — put it behind an authenticating proxy first.

## Reading the verdicts

| Verdict | Meaning |
|---------|---------|
| **PASS** | Install, tests, `release_check`, manifest determinism, secret scan, and GitHub behavior all succeeded locally. Safe to push/release. |
| **PARTIAL** | All local gates pass, but GitHub auth/network is unavailable, so live activity could not be collected (it failed closed, as designed). |
| **FAIL** | Tests or `release_check` failed. Do not push. Read the first failure in `artifacts/release_check_summary.json`, fix the source, rerun. |

`final_status` from `cmar runtime` is the repository's own integrated gate
(`PASS`/`PARTIAL`/`FAIL`); GitHub activity is auxiliary and never raises it.

## Handling missing `gh` auth

If `gh auth status` fails, `cmar github-activity` is **expected** to:

```json
{ "authenticated": false, "collection_errors": ["gh_auth_missing"] }
```

and exit non-zero. This is correct fail-closed behavior, not a bug. Run
`gh auth login` (or export a `GITHUB_TOKEN` / fine-grained PAT in the
environment) and retry. Never hardcode a token or commit a `.env`.

## Regenerating artifacts

Generated artifacts under `artifacts/` are **not** tracked and are not proof of
state on their own — regenerate them in the current run:

```bash
cmar runtime . --out artifacts/self_runtime.json
python scripts/generate_manifest.py   # rewrites RELEASE_MANIFEST.json deterministically
```

`RELEASE_MANIFEST.json` is the only artifact that is committed; it is produced
solely by `scripts/generate_manifest.py` — never hand-edit it.

## Verifying no secrets are committed

```bash
grep -RInE "(ghp_|github_pat_|GITHUB_TOKEN|Authorization: token|Bearer )" . \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=dist --exclude-dir=build || true
```

Only documentation env-var names, the obviously-fake test sentinel, and the
redaction regex should appear. No real token value may be present.
