"""
n7x CLI — engineering audit pipeline.
All commands: deterministic, fail-closed, JSON output, returncode 0 on success.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _write(data: dict, out: str | None) -> None:
    text = json.dumps(data, indent=2)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            f.write(text)
        print(f"→ {out}")
    else:
        print(text)


def cmd_collect(args: argparse.Namespace) -> int:
    from n7x.collectors import account as acc
    snap = acc.collect(args.handle, args.window)
    from n7x.storage import _snap_to_dict
    _write(_snap_to_dict(snap), args.out)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from n7x.collectors import account as acc
    from n7x.scorers import debt
    from n7x.storage import _snap_to_dict
    snap = acc.collect(args.handle, args.window)
    debt.score_account(snap)
    _write(_snap_to_dict(snap), args.out)
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    from n7x.pipeline.normalizer import normalize_from_snapshot
    from n7x.collectors import account as acc
    from n7x.scorers import debt
    snap = acc.collect(args.handle, args.window)
    debt.score_account(snap)
    result = normalize_from_snapshot(snap)
    _write(result, args.out)
    return 0


def cmd_quantize(args: argparse.Namespace) -> int:
    from n7x.pipeline.normalizer import normalize_from_snapshot
    from n7x.pipeline.quantizer import quantize
    from n7x.collectors import account as acc
    from n7x.scorers import debt
    snap = acc.collect(args.handle, args.window)
    debt.score_account(snap)
    norm = normalize_from_snapshot(snap)
    result = quantize(norm)
    _write(result, args.out)
    return 0


def cmd_falsify(args: argparse.Namespace) -> int:
    from n7x.pipeline.falsifier import falsify_from_snapshot
    from n7x.collectors import account as acc
    from n7x.scorers import debt
    snap = acc.collect(args.handle, args.window)
    debt.score_account(snap)
    result = falsify_from_snapshot(snap)
    _write(result, args.out)
    return 0


def cmd_integrate(args: argparse.Namespace) -> int:
    from n7x.pipeline.integrator import run_pipeline
    result = run_pipeline(args.handle, args.window)
    _write(result, args.out)
    return 0


def cmd_delta(args: argparse.Namespace) -> int:
    from n7x import storage
    prev = storage.load_previous()
    latest_path = os.path.join(
        os.environ.get("N7X_DATA_DIR", "data"), "latest.json"
    )
    if not os.path.exists(latest_path):
        print("ERROR: no latest.json — run n7x integrate first", file=sys.stderr)
        return 1
    with open(latest_path) as f:
        current = json.load(f)
    delta = {
        "current_debt":  current.get("total_debt_score"),
        "current_gcei":  current.get("gcei_score"),
        "prev_debt":     prev.get("total_debt_score") if prev else None,
        "prev_gcei":     prev.get("gcei_score") if prev else None,
        "debt_delta":    current.get("debt_delta"),
        "gcei_delta":    current.get("gcei_delta"),
        "collected_at":  current.get("collected_at"),
    }
    _write(delta, args.out)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    from n7x import storage
    runs = storage.load_history(n=args.n)
    result = {
        "runs": [
            {
                "collected_at": r.get("collected_at"),
                "debt_score":   r.get("total_debt_score"),
                "gcei_score":   r.get("gcei_score"),
                "debt_level":   r.get("debt_level"),
                "gcei_level":   r.get("gcei_level"),
            }
            for r in runs
        ]
    }
    _write(result, args.out)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Self-check: verify all pipeline modules importable and functional."""
    checks: list[dict] = []

    modules = [
        "n7x.models",
        "n7x.gh",
        "n7x.collectors.repo",
        "n7x.collectors.account",
        "n7x.scorers.debt",
        "n7x.storage",
        "n7x.renderers.readme",
        "n7x.pipeline.normalizer",
        "n7x.pipeline.quantizer",
        "n7x.pipeline.falsifier",
        "n7x.pipeline.integrator",
    ]
    for mod in modules:
        try:
            __import__(mod)
            checks.append({"module": mod, "status": "OK"})
        except ImportError as e:
            checks.append({"module": mod, "status": "FAIL", "error": str(e)})

    token_ok = bool(os.environ.get("GH_TOKEN"))
    checks.append({"check": "GH_TOKEN", "status": "OK" if token_ok else "MISSING"})

    failed = [c for c in checks if c.get("status") not in ("OK",)]
    result = {
        "checks":  checks,
        "passed":  len(checks) - len(failed),
        "failed":  len(failed),
        "verdict": "PASS" if not failed else "FAIL",
    }
    _write(result, args.out)
    return 0 if not failed else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="n7x", description="n7x engineering audit")
    parser.add_argument("--version", action="version", version="n7x 2.0.0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def _add(name: str, help_: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        p.add_argument("handle", nargs="?",
                       default=os.environ.get("GH_HANDLE", "neuron7xLab"))
        p.add_argument("--window", type=int,
                       default=int(os.environ.get("WINDOW_DAYS", "90")))
        p.add_argument("--out", default=None)
        return p

    _add("collect",   "collect raw GitHub metrics")
    _add("score",     "collect + score debt/GCEI")
    _add("normalize", "normalize signals to [0,1] space")
    _add("quantize",  "compress to VOID/WEAK/PARTIAL/STRONG/RELEASE state")
    _add("falsify",   "adversarial falsification check")
    _add("integrate", "full pipeline: collect→normalize→quantize→falsify→store→render")

    dp = sub.add_parser("delta", help="show debt/GCEI delta vs previous run")
    dp.add_argument("--out", default=None)

    hp = sub.add_parser("history", help="show last N audit runs")
    hp.add_argument("--n", type=int, default=10)
    hp.add_argument("--out", default=None)

    doc = sub.add_parser("doctor", help="self-check all pipeline modules")
    doc.add_argument("--out", default=None)

    args = parser.parse_args()
    dispatch = {
        "collect":   cmd_collect,
        "score":     cmd_score,
        "normalize": cmd_normalize,
        "quantize":  cmd_quantize,
        "falsify":   cmd_falsify,
        "integrate": cmd_integrate,
        "delta":     cmd_delta,
        "history":   cmd_history,
        "doctor":    cmd_doctor,
    }
    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        sys.exit(1)
    try:
        code = fn(args)
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
