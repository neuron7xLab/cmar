# Runtime Chapter 1: Scanner

The scanner converts filesystem matter into a typed artifact state. It computes file count, byte mass, layer distribution, artifact hash, missing surfaces, and risk flags. The scanner output is the input for normalization, void detection, ledger construction, and protocol validation.

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
