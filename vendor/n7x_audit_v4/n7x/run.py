#!/usr/bin/env python3
"""
n7x — full engineering audit pipeline.
Collect → Score → Delta → Save → Render → Done.
Cron: twice daily (06:00 + 18:00 UTC).
"""
from __future__ import annotations
import os
import sys
import json
import time

# Allow running as script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from n7x.collectors import account as acc_collector
from n7x.scorers import debt as debt_scorer
from n7x import storage
from n7x.renderers import readme as readme_renderer
from n7x.storage import _snap_to_dict


def main() -> None:
    handle = os.environ.get("GH_HANDLE", "neuron7xLab")
    window = int(os.environ.get("WINDOW_DAYS", "90"))

    if not os.environ.get("GH_TOKEN"):
        print("ERROR: GH_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    print(f"{'='*60}")
    print(f"n7x audit · {handle} · window={window}d")
    print(f"{'='*60}")

    # 1. Collect
    print("\n[COLLECT]")
    snap = acc_collector.collect(handle, window)

    # 2. Score
    print("\n[SCORE]")
    debt_scorer.score_account(snap)

    # 3. Delta
    print("\n[DELTA]")
    previous = storage.load_previous()
    storage.compute_deltas(snap, previous)
    if snap.debt_delta is not None:
        arrow = "↑ GROWING" if snap.debt_delta > 0 else "↓ SHRINKING"
        print(f"  debt delta: {snap.debt_delta:+.1f} ({arrow})")
    if snap.gcei_delta is not None:
        print(f"  gcei delta: {snap.gcei_delta:+.1f}")

    # 4. Save
    print("\n[SAVE]")
    snap_dict = _snap_to_dict(snap)
    hpath = storage.save(snap)
    print(f"  saved: {hpath}")

    # 5. Render README
    print("\n[RENDER]")
    history = storage.load_history(n=10)
    history_dicts = [_snap_to_dict(h) if not isinstance(h, dict) else h for h in history]

    root = os.path.dirname(os.path.abspath(__file__))
    readme_renderer.write(snap_dict, history_dicts, root)

    # 6. Print summary
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"DEBT  SCORE: {snap.total_debt_score:.1f}/100 [{snap.debt_level}]")
    print(f"GCEI  SCORE: {snap.gcei_score:.1f}/100  [{snap.gcei_level}]")
    print(f"CONFIDENCE:  {snap.confidence.value}")
    print(f"ELAPSED:     {elapsed:.0f}s")
    print(f"{'='*60}")

    # Critical findings to stdout
    all_crits = [
        s for rs in snap.repos for s in rs.signals
        if s.severity in ("CRITICAL", "HIGH")
    ] + [s for s in snap.global_signals if s.severity in ("CRITICAL", "HIGH")]

    if all_crits:
        print(f"\nCRITICAL/HIGH findings ({len(all_crits)}):")
        for s in all_crits:
            print(f"  {'❌' if s.severity=='CRITICAL' else '⚠️ '} [{s.category}] {s.name}: {s.finding[:80]}")

    if snap.hard_caps:
        print(f"\nHard caps ({len(snap.hard_caps)}):")
        for c in snap.hard_caps:
            print(f"  🔴 {c}")


if __name__ == "__main__":
    main()
