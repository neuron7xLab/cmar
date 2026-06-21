# CMAR Release Verdict

## Version

1.4.1

## Status

```text
FINAL_PUSH_READY
DOCTOR_DEFAULT_FIXED
CORPUS_WIRED_TO_TESTS_AND_RELEASE_GATE
PLACEHOLDER_DOCS_REPLACED
```

## Machine Gates

```text
python -m unittest discover -s tests
python scripts/release_check.py
cmar doctor
cmar corpus-eval benchmark_corpus/runtime_v13/artifact_state_stress.jsonl --limit 256
```

## Verdict

CMAR v1.4.1 is the corrected push-ready package. The previously noted `cmar doctor` CLI defect is fixed. Runtime docs are no longer 116-byte placeholders. The benchmark corpus is consumed by tests and the release gate.
