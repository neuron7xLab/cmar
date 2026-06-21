# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CMAR command-line surface — 12 deterministic, JSON-emitting subcommands."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .autofill import autofill
from .doctor import doctor
from .falsifier import falsify
from .integrator import integrate
from .ledger import build_ledger
from .model import stable_json
from .normalizer import normalize
from .plan import build_plan
from .protocol import validate_protocol
from .quantizer import quantize
from .repair import apply_repairs
from .scan import scan_repo
from .voids import build_void_graph

# command name -> callable(repo) -> dict
_COMMANDS = {
    "scan": scan_repo,
    "normalize": normalize,
    "quantize": quantize,
    "voids": build_void_graph,
    "plan": build_plan,
    "repair": apply_repairs,
    "autofill": autofill,
    "protocol": validate_protocol,
    "integrate": integrate,
    "falsify": falsify,
    "ledger": build_ledger,
    "doctor": doctor,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmar", description=__doc__)
    parser.add_argument("--version", action="version", version=f"cmar {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in _COMMANDS:
        sp = sub.add_parser(name, help=f"run the {name} stream")
        sp.add_argument("repo", help="path to the target repository")
        sp.add_argument("--out", help="write JSON output to this path")
    args = parser.parse_args(argv)

    try:
        result = _COMMANDS[args.command](args.repo)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"cmar {args.command}: {exc}", file=sys.stderr)
        return 2

    text = stable_json(result)
    if args.out:
        from pathlib import Path
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        # concise stdout summary for humans + scripts
        summary = {k: result[k] for k in result if k.endswith("verdict")
                   or k in ("overall_state", "release_verdict", "status", "improved",
                            "readiness_score", "blocking_voids", "healthy")}
        print(json.dumps(summary or {"command": args.command}, sort_keys=True))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
