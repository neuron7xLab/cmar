# CMAR Quickstart v1.5.0

```bash
python -m pip install -e .
python -m unittest discover -s tests
python scripts/release_check.py
```

## Inspect current repository

```bash
cmar doctor
cmar doctor . --out artifacts/doctor_report.json --markdown artifacts/doctor_report.md
```

## Run core pipeline

```bash
cmar scan examples/seed_14kb_intent --out artifacts/scan_report.json
cmar normalize examples/seed_14kb_intent --out artifacts/normalized_state.json
cmar quantize examples/seed_14kb_intent --out artifacts/quantized_state.json
cmar falsify examples/seed_14kb_intent --out artifacts/falsification_report.json
cmar integrate examples/seed_14kb_intent --out artifacts/integrated_state.json
```

## Fuse external audit package

```bash
cmar integrate examples/seed_14kb_intent --audit-package data/external_audit_seed/n7x-audit-v4.zip --out artifacts/fused_integrated_state.json
```

## Real GitHub activity (secure local auth only)

```bash
gh auth status   # or: gh auth login
cmar github-activity neuron7xLab --days 30 --out artifacts/github_activity_30d.json
cmar integrate . --github-activity artifacts/github_activity_30d.json --out artifacts/integrated_state_with_github.json
cmar runtime . --github-owner neuron7xLab --days 30 --out artifacts/runtime_real_account.json
```
