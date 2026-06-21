# Runtime Chapter 5: Repair Planning

The planner converts void nodes into prioritized repair actions. Priority is derived from severity, blocking impact, and estimated valid byte gain. The repair plan is not prose; it is machine-readable work order state.

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
