# Runtime Chapter 2: Normalization

Normalization maps heterogeneous repository signals into a comparable unit interval. Raw bytes, binary surface presence, void pressure, protocol state, and release pressure are transformed into a shared numerical vector so structure remains visible after scale noise is removed.

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
