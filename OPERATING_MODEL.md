# CMAR Operating Model v1.4.1

## Execution modes

### Local diagnosis

```bash
cmar doctor
cmar doctor . --out artifacts/doctor_report.json
```

### Runtime state transformation

```bash
cmar normalize <repo>
cmar quantize <repo>
cmar falsify <repo>
cmar integrate <repo>
```

### Materialization

```bash
cmar autofill <repo>
```

### External audit fusion

```bash
cmar integrate <repo> --audit-package data/external_audit_seed/n7x-audit-v4.zip
```

## Completion rule

A repository is not considered release-ready because it has many files. It is release-ready only when the integrated state survives protocol validation and falsification while the ledger has no blocking voids.

## Failure states

- `VOID_BLOCKED`: structural blockers exist.
- `FALSIFIED`: a critical invariant failed.
- `PROTOCOL_REJECTED`: payload is internally inconsistent.
- `REPAIR_REQUIRED`: state is measurable but below release threshold.
- `RELEASE_CANDIDATE`: integrated gate passes.
