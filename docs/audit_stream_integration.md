# Audit Stream Integration v1.4.1

CMAR now accepts an external audit package as an independent computational stream.

```text
CMAR runtime stream + N7X audit stream -> audit projection -> fused integrated verdict
```

The external package is not copied as decoration. It is scanned, hashed, symbol-parsed, projected into a capability vector, then fused with CMAR integrated state.

## Commands

```bash
cmar audit-scan data/external_audit_seed/n7x-audit-v4.zip --out artifacts/audit_snapshot.json
cmar audit-project data/external_audit_seed/n7x-audit-v4.zip --out artifacts/audit_projection.json
cmar integrate examples/seed_14kb_intent --audit-package data/external_audit_seed/n7x-audit-v4.zip --out artifacts/fused_integrated_state.json
cmar audit-fuse examples/seed_14kb_intent --audit-package data/external_audit_seed/n7x-audit-v4.zip --out artifacts/fused_integrated_state.json
```

## Linkage invariant

A stream is valid only if its output becomes another stream's input.
