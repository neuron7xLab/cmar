# Runtime Chapter 4: Void Graph

The Void Graph turns absence into release-blocking evidence. Missing tests, CI, package metadata, schemas, security policy, entrypoints, and release metadata are represented as typed nodes with severity, weight, recommended action, and blocking status.

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
