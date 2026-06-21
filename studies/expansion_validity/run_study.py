#!/usr/bin/env python3
"""Empirical validity study of CMAR's future-state expansion projector.

We do NOT fabricate ledger histories. We drive real repositories through real
edit processes and MEASURE each state with CMAR's actual scanner + ledger, then
test whether velocity-based extrapolation predicts the measured future.

Research questions:
  Q1 which velocity axes are significant predictors (OLS slope, R2, t-stat)
  Q2 when is linear extrapolation sufficient vs insufficient
  Q3 minimum history n for a stable (HIGH-confidence) velocity estimate
  Q4 does expansion_verdict==DIVERGING track the real direction of the system

Validity criterion:  |proj_mass - actual_mass| / actual_mass < 0.15  at H=5
Falsification:       if predicted direction ~ chance -> no predictive power.
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from cmar.scanner import scan_repository
from cmar.voids import build_void_graph
from cmar.ledger import build_mass_ledger
from cmar.expander import compute_expansion

HORIZON = 5
STEPS = 20
SEED = 1729
OUT = Path(__file__).resolve().parent
WORK = Path("/tmp/cmar_study_work")


# ---------- pure-python OLS (no numpy dependency) ----------
def ols(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0, 1.0, float("inf"), 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    yhat = [intercept + slope * x for x in xs]
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    if n > 2 and sxx:
        s2 = ss_res / (n - 2)
        se = (s2 / sxx) ** 0.5
    else:
        se = float("inf")
    t = slope / se if se not in (0.0, float("inf")) else 0.0
    return slope, intercept, r2, se, t


# ---------- real repo state measurement ----------
def _write(p: Path, nbytes: int):
    p.parent.mkdir(parents=True, exist_ok=True)
    # real, scannable source content of a controlled size
    body = "# generated module\n" + ("x = 1  # pad\n" * max(nbytes // 12, 1))
    p.write_text(body[:max(nbytes, 20)], encoding="utf-8")


def _surfaces(root: Path):
    """Create the non-source surfaces so blocking_voids start at 0."""
    (root / "pyproject.toml").write_text(
        '[project]\nname="t"\nversion="0.1.0"\n[project.scripts]\nt="t.cli:main"\n', encoding="utf-8")
    _write(root / "src/t/cli.py", 200)
    _write(root / "src/t/__init__.py", 30)
    _write(root / "tests/test_t.py", 200)
    (root / ".github/workflows/ci.yml").parent.mkdir(parents=True, exist_ok=True)
    (root / ".github/workflows/ci.yml").write_text("name: CI\non: [push]\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
    (root / "schemas").mkdir(exist_ok=True)
    (root / "schemas/a.schema.json").write_text("{}\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/readme.md").write_text("# Docs\n", encoding="utf-8")


def measure(root: Path) -> dict:
    scan = scan_repository(root)
    voids = build_void_graph(scan)
    ledger = build_mass_ledger(scan, voids, 1048576)
    d = ledger.to_dict()
    return {"valid_mass_bytes": d["valid_mass_bytes"], "blocking_voids": d["blocking_voids"],
            "voids_detected": d["voids_detected"]}


def trajectory(name: str) -> list[dict]:
    rng = random.Random(SEED + sum(ord(c) for c in name))
    root = WORK / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    _surfaces(root)
    snaps = []

    if name == "degradation":
        for i in range(25):
            _write(root / f"src/t/mod_{i}.py", 1200)
    snaps.append(measure(root))

    for step in range(1, STEPS):
        if name == "steady":
            _write(root / f"src/t/mod_{step}.py", 1200)
        elif name == "saturating":
            _write(root / f"src/t/mod_{step}.py", int(2200 * (0.72 ** step)) + 25)
        elif name == "degradation":
            f = root / f"src/t/mod_{step}.py"
            if f.exists():
                f.unlink()
            if step == 8:  # remove the test surface -> blocking void appears
                shutil.rmtree(root / "tests", ignore_errors=True)
            if step == 12:  # remove CI surface -> another blocking void
                shutil.rmtree(root / ".github", ignore_errors=True)
        elif name == "noisy":
            _write(root / f"src/t/mod_{step}.py", 1000 + rng.randint(-700, 900))
            if step % 4 == 0:
                victim = root / f"src/t/mod_{max(step - 3, 1)}.py"
                if victim.exists():
                    victim.unlink()
        snaps.append(measure(root))
    return snaps


# ---------- evaluation ----------
def verdict_dir(vel_mass, vel_voids_closed):
    if vel_mass < 0 or vel_voids_closed < 0:
        return "DIVERGING"
    if vel_mass == 0 and vel_voids_closed == 0:
        return "STABLE"
    return "CONVERGING"


def evaluate(name, snaps):
    mass = [s["valid_mass_bytes"] for s in snaps]
    voids = [s["blocking_voids"] for s in snaps]
    rows = []
    for k in range(2, STEPS - HORIZON):  # train on first k, predict k-1+H
        idx_now = k - 1
        idx_future = idx_now + HORIZON
        xs = list(range(k))
        ys = mass[:k]
        slope, intercept, r2, se, t = ols(xs, ys)
        # shipped two-endpoint velocity (as in expander.compute_expansion)
        vel_end = (mass[idx_now] - mass[0]) / idx_now
        voids_closed_end = (voids[0] - voids[idx_now]) / idx_now
        proj_ols = intercept + slope * idx_future
        proj_end = mass[idx_now] + vel_end * HORIZON
        actual = mass[idx_future]
        denom = max(abs(actual), 1)
        err_ols = abs(proj_ols - actual) / denom
        err_end = abs(proj_end - actual) / denom
        # direction agreement (predicted vs actual future delta)
        pred_verdict = verdict_dir(vel_end, voids_closed_end)
        actual_mass_dir = mass[idx_future] - mass[idx_now]
        actual_voids_dir = voids[idx_now] - voids[idx_future]  # +ve = closing
        actual_verdict = verdict_dir(actual_mass_dir, actual_voids_dir)
        rows.append({
            "k": k, "r2": round(r2, 4), "slope": round(slope, 2),
            "rel_se": round(se / abs(slope), 4) if slope and se != float("inf") else None,
            "t_stat": round(t, 3) if t else None,
            "err_ols": round(err_ols, 4), "err_end": round(err_end, 4),
            "pred_verdict": pred_verdict, "actual_verdict": actual_verdict,
            "dir_match": pred_verdict == actual_verdict,
        })
    return {"name": name, "mass": mass, "voids": voids, "rows": rows}


def summarize(results):
    out = {"horizon": HORIZON, "steps": STEPS, "criterion": 0.15, "trajectories": {}}
    all_match = []
    for r in results:
        rows = r["rows"]
        e_ols = [x["err_ols"] for x in rows]
        e_end = [x["err_end"] for x in rows]
        matches = [x["dir_match"] for x in rows]
        all_match += matches
        # Q3: smallest k with stable slope (rel SE < 0.25)
        min_stable_k = next((x["k"] for x in rows if x["rel_se"] is not None and x["rel_se"] < 0.25), None)
        out["trajectories"][r["name"]] = {
            "mean_err_ols": round(sum(e_ols) / len(e_ols), 4),
            "mean_err_end": round(sum(e_end) / len(e_end), 4),
            "max_err_ols": round(max(e_ols), 4),
            "max_err_end": round(max(e_end), 4),
            "frac_within_0.15_ols": round(sum(1 for e in e_ols if e < 0.15) / len(e_ols), 3),
            "frac_within_0.15_end": round(sum(1 for e in e_end if e < 0.15) / len(e_end), 3),
            "dir_match_rate": round(sum(matches) / len(matches), 3),
            "min_stable_k_relSE<0.25": min_stable_k,
            "final_mass": r["mass"][-1], "final_blocking_voids": r["voids"][-1],
        }
    out["overall_dir_match_rate"] = round(sum(all_match) / len(all_match), 3)
    out["overall_dir_match_n"] = len(all_match)
    return out


def main():
    names = ["steady", "saturating", "degradation", "noisy"]
    results = [evaluate(n, trajectory(n)) for n in names]
    summary = summarize(results)
    (OUT / "evidence.json").write_text(
        json.dumps({"summary": summary, "detail": results}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
