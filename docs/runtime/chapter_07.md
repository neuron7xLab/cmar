# Runtime Chapter 7: Protocol Validation

Protocol validation checks the internal consistency of payloads. It rejects missing top-level fields, ledger hash mismatch, incorrect void counts, impossible mass values, and blocking voids that do not block release.

## Input

The input is an upstream CMAR state object, a repository path, or an external audit package depending on the module.

## Output

The output is JSON-serializable state that becomes the next module's input.

## Acceptance gate

```text
output exists
output is deterministic
output is machine-readable
output feeds a downstream module
```

## Runtime invariant

```text
A module is valid only if another module consumes its output.
```
