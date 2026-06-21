# Runtime Chapter 3: Quantization

Quantization compresses continuous normalized values into discrete operational categories: VOID, WEAK, PARTIAL, STRONG, RELEASE. Thresholds are explicit in JSON and information loss is reported, so interpretability is gained without hiding compression cost.

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
