# CMAR Architecture v1.4.1

CMAR is a cognitive artifact-materialization runtime. It converts incomplete repository intent into a validated machine-checkable artifact state.

## Runtime chain

```text
repository -> scan -> normalize -> quantize -> void graph -> repair plan -> protocol -> falsifier -> ledger -> integrated verdict
```

## Operational principle

A module is accepted only when its output becomes another module's input. A report that does not change downstream state is not part of the runtime.

## Core modules

| Module | Input | Output | Gate |
|---|---|---|---|
| scanner | repository path | ScanReport | artifact hash + layer mass |
| normalizer | scan + ledger + protocol | NormalizationReport | comparable signal vector |
| quantizer | normalized vector | QuantizationReport | discrete release bucket |
| voids | scan | VoidGraph | typed release blockers |
| planner | void graph | RepairPlan | prioritized repairs |
| autofill | repo + void state | AutofillReport | valid mass increase |
| protocol | payload | ProtocolReport | schema + semantic invariants |
| falsifier | integrated payload | FalsificationReport | attempts to invalidate release |
| ledger | scan + voids | MassLedger | release status |
| integrator | all streams | IntegratedState | final machine verdict |
| audit_stream | external audit package | AuditProjection | external stream fused into CMAR |

## Non-negotiable release invariants

```text
No evidence, no release.
No validated capability, no product.
No protocol verdict, no completion.
No fused stream, no claimed integration.
```
