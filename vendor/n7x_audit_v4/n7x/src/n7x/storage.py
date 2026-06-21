"""
n7x.storage — persist snapshots, compute deltas.
"""
from __future__ import annotations
import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

DATA_DIR = os.environ.get("N7X_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
HISTORY_DIR = os.path.join(DATA_DIR, "history")
LATEST_PATH = os.path.join(DATA_DIR, "latest.json")


def _ensure_dirs() -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)


def _snap_to_dict(snap: Any) -> dict:
    """Convert dataclass to JSON-serializable dict."""
    from n7x.models import AccountSnapshot
    d = asdict(snap)
    # convert Enum values to strings
    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(i) for i in obj]
        if hasattr(obj, "value"):  # Enum
            return obj.value
        return obj
    return _clean(d)


def save(snap: Any) -> str:
    """Save snapshot to history/ and latest.json. Returns history file path."""
    _ensure_dirs()
    d = _snap_to_dict(snap)

    # history file
    ts    = snap.collected_at.replace(":", "-").replace("T", "_")[:16]
    fname = f"{snap.handle}_{ts}.json"
    hpath = os.path.join(HISTORY_DIR, fname)
    with open(hpath, "w") as f:
        json.dump(d, f, indent=2)

    # latest
    with open(LATEST_PATH, "w") as f:
        json.dump(d, f, indent=2)

    return hpath


def load_previous() -> dict | None:
    """Load the second-most-recent snapshot for delta computation."""
    _ensure_dirs()
    files = sorted(
        [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")],
        reverse=True
    )
    if len(files) < 2:
        return None
    path = os.path.join(HISTORY_DIR, files[1])
    with open(path) as f:
        return json.load(f)


def compute_deltas(current: Any, previous: dict | None) -> None:
    """Attach debt_delta and gcei_delta to current snapshot."""
    if previous is None:
        return
    prev_debt = previous.get("total_debt_score")
    prev_gcei = previous.get("gcei_score")
    if prev_debt is not None:
        current.debt_delta = round(current.total_debt_score - prev_debt, 1)
    if prev_gcei is not None:
        current.gcei_delta = round(current.gcei_score - prev_gcei, 1)


def load_history(n: int = 10) -> list[dict]:
    """Load last N historical snapshots for trend rendering."""
    _ensure_dirs()
    files = sorted(
        [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")],
        reverse=True
    )[:n]
    result = []
    for f in files:
        with open(os.path.join(HISTORY_DIR, f)) as fh:
            result.append(json.load(fh))
    return list(reversed(result))  # oldest first
