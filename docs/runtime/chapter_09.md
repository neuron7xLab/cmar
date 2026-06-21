# Runtime Chapter 9: Audit Stream Fusion

The audit stream imports an external audit package, scans its files, projects its capabilities into CMAR-compatible signals, and fuses those signals with the integrated repository state. This creates a state no isolated module can produce.

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
