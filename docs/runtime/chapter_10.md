# Runtime Chapter 10: Release Gate

The release gate runs tests, normalization, quantization, falsification, audit fusion, and autofill. The repository can be called ready only when the gate emits CMAR RELEASE CHECK: PASS and artifacts are regenerated deterministically.

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
