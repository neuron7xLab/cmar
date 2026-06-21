# CMAR Demo Script v1.4.1

```bash
set -euo pipefail
python -m pip install -e .
python -m unittest discover -s tests
python scripts/release_check.py
cmar doctor --out artifacts/doctor_default_root.json
cmar integrate examples/seed_14kb_intent --audit-package data/external_audit_seed/n7x-audit-v4.zip --out artifacts/fused_integrated_state.json
```

Expected final line from release check:

```text
CMAR RELEASE CHECK: PASS
```
