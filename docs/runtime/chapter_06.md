# Runtime Chapter 6: Autofill

Autofill materializes missing repository structure only when voids justify it. It creates package metadata, tests, CI, security policy, schemas, release verdict, documentation, and artifacts. Success requires increased valid mass and non-increasing blocking void count.

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
