"""
n7x.pipeline.integrator
Connects independent streams: collect→score→normalize→quantize→falsify→store→render.
Output of each stage becomes input of next.
The integrated state is what no single module could produce alone.
"""
from __future__ import annotations
import os
from n7x.collectors import account as acc_collector
from n7x.scorers import debt as debt_scorer
from n7x.pipeline.normalizer import normalize_from_snapshot
from n7x.pipeline.quantizer import quantize
from n7x.pipeline.falsifier import falsify_from_snapshot
from n7x import storage
from n7x.storage import _snap_to_dict
from n7x.renderers import readme as readme_renderer


def run_pipeline(handle: str, window: int) -> dict:
    """
    Full n7x pipeline. Returns integrated_state.json content.
    Each stage output is the next stage's input.
    """
    root = os.environ.get("N7X_ROOT", os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ))

    # Stage 1: collect
    print("[pipeline:1/7] collect")
    snap = acc_collector.collect(handle, window)

    # Stage 2: score (uses snap → enriches snap in-place)
    print("[pipeline:2/7] score")
    debt_scorer.score_account(snap)

    # Stage 3: delta (uses storage history)
    print("[pipeline:3/7] delta")
    previous = storage.load_previous()
    storage.compute_deltas(snap, previous)

    # Stage 4: normalize (uses scored snap)
    print("[pipeline:4/7] normalize")
    norm_state = normalize_from_snapshot(snap)

    # Stage 5: quantize (uses norm_state)
    print("[pipeline:5/7] quantize")
    quant_state = quantize(norm_state)

    # Stage 6: falsify (uses scored snap)
    print("[pipeline:6/7] falsify")
    falsif_state = falsify_from_snapshot(snap)

    # Stage 7: store + render
    print("[pipeline:7/7] store+render")
    snap_dict = _snap_to_dict(snap)
    storage.save(snap)
    history = storage.load_history(n=10)
    history_dicts = [h if isinstance(h, dict) else _snap_to_dict(h) for h in history]
    readme_renderer.write(snap_dict, history_dicts, root)

    # Integrated state: only possible because all stages ran and connected
    integrated = {
        "schema":      "n7x/integrated_state/v1",
        "handle":      handle,
        "collected_at": snap.collected_at,
        "window_days":  window,
        # From scorer
        "debt_score":   snap.total_debt_score,
        "debt_level":   snap.debt_level,
        "gcei_score":   snap.gcei_score,
        "gcei_level":   snap.gcei_level,
        "confidence":   snap.confidence.value,
        # From delta
        "debt_delta":   snap.debt_delta,
        "gcei_delta":   snap.gcei_delta,
        # From normalizer
        "blocking_signals": norm_state.get("blocking_signals", []),
        "blocking_count":   norm_state.get("blocking_count", 0),
        "void_pressure":    norm_state["signals"]["void_pressure"]["value"],
        "release_blocking_pressure": norm_state["signals"]["release_blocking_pressure"]["value"],
        # From quantizer
        "quantized_state":  quant_state["composite"]["state"],
        "quantized_verdict": quant_state["verdict"],
        "hard_overrides":   quant_state.get("hard_overrides", []),
        # From falsifier
        "falsification_verdict":  falsif_state["verdict"],
        "falsified_checks":       falsif_state.get("falsified_checks", []),
        # Integrated verdict — requires all stages to agree
        "integrated_verdict": _integrate_verdict(snap, quant_state, falsif_state),
        # Risk axes
        "risks": {
            "sustainability": snap.risk_sustainability,
            "accumulation":   snap.risk_accumulation,
            "isolation":      snap.risk_isolation,
            "stability":      snap.risk_stability,
        },
        "hard_caps":               snap.hard_caps,
        "anti_gaming_penalties":   snap.anti_gaming_penalties,
        "history_runs":            len(history),
    }
    return integrated


def _integrate_verdict(snap: object, quant: dict, falsif: dict) -> str:
    """
    Integrated verdict requires agreement from all three stages.
    No single stage can produce this verdict alone.
    """
    q_state = quant["composite"]["state"]
    f_verdict = falsif["verdict"]
    debt = getattr(snap, "total_debt_score", 100.0)
    gcei = getattr(snap, "gcei_score", 0.0)

    if f_verdict == "FALSIFIED":
        return "BLOCKED_BY_FALSIFICATION"
    if q_state == "VOID":
        return "BLOCKED_VOID_STATE"
    if debt >= 70:
        return "BLOCKED_TERMINAL_DEBT"
    if q_state == "WEAK":
        return "CONDITIONAL_WEAK"
    if f_verdict == "PARTIAL" or q_state == "PARTIAL":
        return "CONDITIONAL_PARTIAL"
    if q_state == "STRONG" and gcei >= 60:
        return "CANDIDATE"
    if q_state == "RELEASE" and f_verdict == "NOT_FALSIFIED" and gcei >= 75:
        return "RELEASE_READY"
    return "CONDITIONAL_PARTIAL"
