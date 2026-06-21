<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Demo

```bash
pip install -e .
python scripts/release_check.py            # CMAR RELEASE CHECK: PASS
cmar integrate examples/seed_14kb_intent   # BLOCKED (seed is honest-incomplete)
cmar autofill /tmp/copy_of_seed            # improved: true
```
The seed is intentionally incomplete; CMAR shows the path to a validated state.
