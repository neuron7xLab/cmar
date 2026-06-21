"""
n7x.renderers.readme — render AccountSnapshot → README.md
Full truth: debt, GCEI, per-repo, trends, velocity, coherence, target gap.
"""
from __future__ import annotations
import json
import os
from typing import Any

ROOT = os.environ.get("N7X_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _bar(v: float, width: int = 24) -> str:
    filled = max(0, min(width, round(v / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def _delta(d: float | None, invert: bool = False) -> str:
    if d is None: return "—"
    sign  = "+" if d > 0 else ""
    emoji = ("🔴" if d > 0 else "🟢") if not invert else ("🟢" if d > 0 else "🔴")
    return f"{emoji} {sign}{d:.1f}"


def _sev_emoji(sev: str) -> str:
    return {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢","OK":"✅"}.get(sev,"⚪")


def _conf_badge(c: str) -> str:
    return {"HIGH":"🔵","MEDIUM":"🟡","LOW":"🟠","NONE":"⛔"}.get(c,"⚪")


def _sparkline(values: list[float]) -> str:
    chars = "▁▂▃▄▅▆▇█"
    if not values: return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    return "".join(chars[min(7, int((v - mn) / rng * 7))] for v in values)


def _velocity_section(history: list[dict]) -> str:
    try:
        from n7x.scorers.velocity import compute_velocity
        vel = compute_velocity(history)
        dv  = vel.get("debt_velocity")
        gv  = vel.get("gcei_velocity")
        tv  = vel.get("trend_verdict", "UNKNOWN")
        p90 = vel.get("projection_90d") or {}
        dv_str = f"{dv:+.2f} pts/run" if dv is not None else "N/A"
        gv_str = f"{gv:+.2f} pts/run" if gv is not None else "N/A"
        block = (
            f"| Debt velocity | {dv_str} | {vel.get('debt_direction_last3','?')} |\n"
            f"| GCEI velocity | {gv_str} | {vel.get('gcei_direction_last3','?')} |\n"
            f"| Trend | **{tv}** | — |\n"
            f"| 90d projection | debt={p90.get('debt','?')} · gcei={p90.get('gcei','?')} | linear |\n"
            f"| Runs used | {vel.get('runs_used','N/A')} | — |\n"
        )
        if vel.get("release_blocked_by_velocity"):
            block += "\n> 🔴 **RELEASE_BLOCKED_BY_VELOCITY**: debt trending up 3+ consecutive runs.\n"
        return block
    except Exception as e:
        return f"_velocity unavailable: {e}_\n"


def _coherence_section(axes: dict[str, float]) -> str:
    try:
        from n7x.scorers.coherence import compute_coherence
        coh = compute_coherence(axes)
        lines = [
            f"| Std dev | {coh.get('stdev','N/A')} |",
            f"| Verdict | **{coh.get('verdict','?')}** |",
            f"| Anomalies | {coh.get('anomaly_count',0)} |",
        ]
        block = "\n".join(lines) + "\n"
        for a in coh.get("anomalies", []):
            se = _sev_emoji(a["severity"])
            block += f"\n- {se} **{a['pattern']}**: {a['description']}\n"
        if not coh.get("anomalies"):
            block += "\n_No structural anomalies._\n"
        return block
    except Exception as e:
        return f"_coherence unavailable: {e}_\n"


def _target_section(axes: dict[str, float]) -> str:
    try:
        from n7x.scorers.target import score_for_target, compare_targets
        tgt_r  = score_for_target(axes, "research")
        tgt_ai = score_for_target(axes, "ai_lab")
        comp   = compare_targets(axes)
        lines = [
            f"| research | **{tgt_r['target_gcei']:.0f}** | {tgt_r['target_level']} |",
            f"| ai_lab   | **{tgt_ai['target_gcei']:.0f}** | {tgt_ai['target_level']} |",
            f"| best_fit | — | {comp.get('best_fit','?')} |",
        ]
        block = "\n".join(lines) + "\n\n**Critical path (research):**\n"
        for g in tgt_r.get("gap_analysis", [])[:4]:
            pe = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(g["priority"],"⚪")
            block += (
                f"- {pe} `{g['axis']}` = {g['current_value']:.2f} "
                f"(weight {g['weight']:.2f}) → +{g['marginal_gain']:.0f}pts if fixed\n"
            )
        return block
    except Exception as e:
        return f"_target unavailable: {e}_\n"


def render(snap: dict, history: list[dict]) -> str:
    handle  = snap["handle"]
    debt    = snap["total_debt_score"]
    dlevel  = snap["debt_level"]
    gcei    = snap["gcei_score"]
    glevel  = snap["gcei_level"]
    ts      = snap["collected_at"]
    window  = snap["window_days"]
    age     = snap["account_age_days"]
    conf    = snap.get("confidence", "LOW")
    risks   = snap.get("risks", {})
    gm      = snap.get("global_metrics", {})
    repos   = snap.get("repos", [])
    g_sig   = snap.get("global_signals", [])
    caps    = snap.get("hard_caps", [])
    aga     = snap.get("anti_gaming_penalties", [])
    bench   = snap.get("benchmarks", {})

    debt_delta = snap.get("debt_delta")
    gcei_delta = snap.get("gcei_delta")

    hist_debt  = [h.get("total_debt_score", 0) for h in history]
    hist_gcei  = [h.get("gcei_score", 0) for h in history]

    def gv(key: str) -> str:
        m = gm.get(key, {})
        v = m.get("value")
        return "N/A" if v is None else str(v)

    def gf(key: str, fmt: str = ".0f") -> str:
        m = gm.get(key, {})
        v = m.get("value")
        if v is None: return "N/A"
        try: return format(float(v), fmt)
        except: return str(v)

    repo_rows = ""
    for r in sorted(repos, key=lambda x: -(x.get("debt_score") or 0)):
        rm     = r.get("metrics", {})
        name   = r["name"]
        dscore = r.get("debt_score", 0)
        dl     = r.get("debt_level", "?")
        ci_f   = (rm.get("ci_fail_rate") or {}).get("value")
        del_r  = (rm.get("deletion_ratio") or {}).get("value")
        ver    = (rm.get("verified_ratio") or {}).get("value")
        bot    = (rm.get("bot_ratio") or {}).get("value")
        lt     = (rm.get("lead_time_p50_hours") or {}).get("value")
        cwt    = (rm.get("churn_without_tests") or {}).get("value")
        hc     = (rm.get("commits_human") or {}).get("value")
        repo_rows += (
            f"| [{name}](https://github.com/{handle}/{name}) "
            f"| **{dscore:.0f}** ({dl}) "
            f"| {f'{del_r:.3f}' if del_r is not None else 'N/A'} "
            f"| {f'{ci_f*100:.0f}%' if ci_f is not None else 'N/A'} "
            f"| {f'{ver*100:.0f}%' if ver is not None else 'N/A'} "
            f"| {f'{bot*100:.0f}%' if bot is not None else 'N/A'} "
            f"| {f'{lt:.1f}h' if lt is not None else 'N/A'} "
            f"| {cwt if cwt is not None else 'N/A'} "
            f"| {hc if hc is not None else 'N/A'} |\n"
        )

    crit_lines = ""
    for s in g_sig:
        if s["severity"] in ("CRITICAL", "HIGH"):
            crit_lines += f"- {_sev_emoji(s['severity'])} **{s['name']}**: {s['finding']}\n"
            if s.get("remediation"):
                crit_lines += f"  - 💊 _{s['remediation']}_\n"

    repo_findings = ""
    for r in repos:
        sigs = r.get("signals", [])
        crit = [s for s in sigs if s["severity"] in ("CRITICAL","HIGH")]
        if crit:
            repo_findings += f"\n**[{r['name']}]**\n"
            for s in crit:
                repo_findings += f"- {_sev_emoji(s['severity'])} `{s['name']}`: {s['finding']}\n"
                if s.get("remediation"):
                    repo_findings += f"  - 💊 _{s['remediation']}_\n"

    caps_block = "\n".join(f"- 🔴 `{c}`" for c in caps) or "_none_"
    aga_block  = "\n".join(f"- ⚠️ `{a}`" for a in aga) or "_none_"

    bench_rows = ""
    for k, v in bench.items():
        if isinstance(v, dict):
            bench_rows += f"| `{k}` | {v.get('healthy','?')} | {v.get('warning','?')} | {v.get('critical','?')} |\n"

    prs_trend  = [gv(f"prs_month_{i}") for i in range(2, -1, -1)]
    trend_str  = " → ".join(prs_trend)
    safe_vals  = [float(x) for x in prs_trend if x != "N/A"]
    trend_spark = _sparkline(safe_vals)

    badge_color = "red" if debt > 50 else "orange" if debt > 30 else "yellow" if debt > 15 else "green"
    gcei_color  = "green" if gcei >= 75 else "yellow" if gcei >= 60 else "orange" if gcei >= 45 else "red"
    debt_slug   = dlevel.replace(" ", "_")
    gcei_slug   = glevel.replace("→","--").replace("/","%2F").replace(" ","_")

    # Axes from stored scores
    snap_scores  = snap.get("scores", {})
    axes_approx  = {k: float(snap_scores.get(k, 0.0)) for k in
                    ["activity","delivery","quality","collaboration",
                     "security","sustainability","evidence"]}

    vel_block = _velocity_section(history)
    coh_block = _coherence_section(axes_approx)
    tgt_block = _target_section(axes_approx)

    readme = f"""<!--
AUTO-GENERATED by n7x pipeline · {ts}
DO NOT EDIT MANUALLY
-->

# 🔬 n7x Engineering Audit · `{handle}`

![debt](https://img.shields.io/badge/debt_score-{debt:.0f}%2F100-{badge_color})
![debt_level](https://img.shields.io/badge/debt_level-{debt_slug}-{badge_color})
![gcei](https://img.shields.io/badge/GCEI-{gcei:.0f}%2F100-{gcei_color})
![gcei_level](https://img.shields.io/badge/level-{gcei_slug}-{gcei_color})
![confidence](https://img.shields.io/badge/confidence-{conf}-darkblue)
![age](https://img.shields.io/badge/account_age-{age}d-gray)
![window](https://img.shields.io/badge/window-{window}d-gray)

> **⚠️ Validity declaration (SPACE §tension + Campbell's Law)**
> Metric vector under tension. Level estimates: heuristic, not peer-validated.
> Self-review only. High-stakes decisions require external peer review.

---

## Summary

| | Now | Δ vs prev | Trend ({len(hist_debt)} runs) |
|---|---|---|---|
| **Debt score** | **{debt:.0f}/100** ({dlevel}) | {_delta(debt_delta, invert=True)} | `{_sparkline(hist_debt)}` |
| **GCEI score** | **{gcei:.0f}/100** ({glevel}) | {_delta(gcei_delta)} | `{_sparkline(hist_gcei)}` |
| **Confidence** | {_conf_badge(conf)} {conf} | — | — |

---

## Critical findings

### Global signals
{crit_lines or "_No critical global signals._"}

### Per-repo signals
{repo_findings or "_No critical repo signals._"}

### Hard caps
{caps_block}

### Anti-gaming penalties
{aga_block}

---

## Repository matrix

| Repo | Debt | Del.ratio | CI fail | Verified | Bots | Lead-time p50 | Churn∅test | Human commits |
|---|---|---|---|---|---|---|---|---|
{repo_rows}
> **Del.ratio** = deletions/additions. Benchmark healthy ≥ 0.25 (Nagappan & Ball, ICSE 2005).

---

## Velocity · Coherence · Target gap

### Velocity (rate of change)

| Metric | Value | Direction (last 3 runs) |
|---|---|---|
{vel_block}

### Coherence (axis variance)

| Metric | Value |
|---|---|
{coh_block}

### Target gap

| Target | GCEI | Level |
|---|---|---|
{tgt_block}

---

## Global activity (`{window}d window`)

| Metric | Value | Provenance |
|---|---|---|
| PRs created | {gv('pr_created')} | `search?q=type:pr author:{handle}` |
| PRs merged | {gv('pr_merged')} | `search?q=is:merged` |
| Reviews given | {gv('reviews_given')} | `search?q=reviewed-by:{handle}` |
| External PRs merged | {gv('ext_pr_merged')} | `search?q=is:merged -user:{handle}` |
| External contributors | {gv('external_contributors')} | `/repos/*/contributors` |
| Bus factor | {gv('bus_factor')} | `/repos/top/stats/contributors` |
| Monthly trend | {trend_str} `{trend_spark}` | monthly search buckets |
| Account age | {age}d | `/users/{handle}.created_at` |

---

## Benchmarks

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
{bench_rows}

> Nagappan & Ball (ICSE 2005) · Kalliamvakou et al. (2016) · DORA 2024 · CHAOSS.
> Thresholds heuristic — not validated for individual leveling.

---

## Risk classification

| Risk axis | Status |
|---|---|
| Sustainability | {"🔴" if "HIGH" in risks.get("sustainability","") or "CRITICAL" in risks.get("sustainability","") else "🟡" if "MEDIUM" in risks.get("sustainability","") else "🟢"} {risks.get("sustainability","N/A")} |
| Accumulation   | {"🔴" if "CRITICAL" in risks.get("accumulation","") else "🟠" if "HIGH" in risks.get("accumulation","") else "🟡" if "MEDIUM" in risks.get("accumulation","") else "🟢"} {risks.get("accumulation","N/A")} |
| Isolation      | {"🔴" if "CRITICAL" in risks.get("isolation","") else "🟠" if "HIGH" in risks.get("isolation","") else "🟡" if "MEDIUM" in risks.get("isolation","") else "🟢"} {risks.get("isolation","N/A")} |
| Stability      | {"🟠" if "HIGH" in risks.get("stability","") else "🟢"} {risks.get("stability","N/A")} |

---

[→ raw latest.json](./data/latest.json) · [→ history](./data/history/) · [→ audit source](./src/n7x/)

_Updated: {ts} · window: {window}d · Fuck sycophancy ⊛_
"""
    return readme


def write(snap: dict, history: list[dict], root: str | None = None) -> None:
    r = root or ROOT
    content = render(snap, history)
    path = os.path.join(r, "README.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"README.md written ({len(content):,} chars) → {path}")
