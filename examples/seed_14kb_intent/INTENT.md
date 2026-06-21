# Intent: minimal task-queue runtime

This seed is raw software *intent*: source that expresses what is wanted, with no
tests, no CI, no schema, and no security policy. It exists so CMAR can demonstrate
the path from intent to a validated artifact state.

Goal: an in-memory priority task queue with deterministic ordering and a small
scheduler. The implementation is real and runnable; the surrounding evidence
infrastructure is deliberately absent — those are the voids CMAR autofills.
