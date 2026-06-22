#!/usr/bin/env python3
"""Compute live owner truth-stats and inject them into README.md between markers.

Run by the daily GitHub Action (and locally). Numbers are computed this run via
`cmar stats` (clone + CMAR scan + gh api). Fail-closed: if GitHub auth is
unavailable the block says so and the script exits non-zero — it never writes
stale or faked numbers.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cmar.stats import compute_owner_stats, render_markdown  # noqa: E402

START = "<!-- CMAR-STATS:START -->"
END = "<!-- CMAR-STATS:END -->"


def main() -> int:
    owner = sys.argv[1] if len(sys.argv) > 1 else "neuron7xLab"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    stats = compute_owner_stats(owner, days=days, scan=True)

    block = f"{START}\n{render_markdown(stats)}{END}"
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if START in text and END in text:
        pre = text.split(START)[0]
        post = text.split(END, 1)[1]
        text = pre + block + post
    else:
        text = text.rstrip() + "\n\n## Live stats\n\n" + block + "\n"
    readme.write_text(text, encoding="utf-8")

    # Persist the raw JSON evidence (gitignored locally; CI may upload as artifact).
    out = ROOT / "artifacts/owner_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    out.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not stats.get("authenticated"):
        print("STATS: fail-closed (no GitHub auth) — README marked, exiting non-zero")
        return 1
    t = stats["totals"]
    print(f"STATS OK: scanned {t['repos_scanned']}/{t['public_repos_listed']} repos, "
          f"debt={t['total_debt_blocking_voids']}, falsified={t['falsified_repos']}, "
          f"crit_vulns={t['total_critical_vulns']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
