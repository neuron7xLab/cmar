# Runtime Chapter 8: Falsification

The falsifier attempts to prove CMAR output invalid. It checks missing evidence layers, invalid protocol state, ledger contradictions, docs-heavy weak executable mass, and release claims that coexist with blocking defects.

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
