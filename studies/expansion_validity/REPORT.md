# Meta-analysis: predictive validity of CMAR's expansion projector

**Method.** Four real repository trajectories (20 steps each) were driven through
real edit processes; every `valid_mass_bytes` and `blocking_voids` was **measured**
by CMAR's actual scanner + ledger — none fabricated. For each training window of
length *k* we projected `H=5` iterations ahead with two estimators — the shipped
two-endpoint velocity and ordinary least squares (OLS) — and compared against the
measured future state. Reproduce: `python studies/expansion_validity/run_study.py`
(seed 1729; raw numbers in `evidence.json`).

**Validity criterion.** `|proj_mass − actual_mass| / actual_mass < 0.15` at H=5.
**Falsification criterion.** if `expansion_verdict` does not track the real
direction of the system, the method has no predictive power and is rejected.

## Results (measured)

| trajectory   | mean err (OLS) | mean err (endpoint) | within 0.15 (OLS) | dir-match | shape |
|--------------|---------------:|--------------------:|------------------:|----------:|-------|
| steady       | 0.000          | 0.000               | 100%              | 100%      | linear |
| degradation  | 0.008          | 0.008               | 100%              | 100%      | linear decline |
| noisy        | 0.131          | 0.163               | 77%               | 100%      | linear + noise |
| saturating   | 0.589          | 0.527               | 0%                | 100%      | concave/asymptotic |

Direction agreement overall: **52/52 windows (1.00)**.

## Answers

**Q1 — which velocity axes predict.** `d(valid_mass)/dt` is a significant
predictor *only when the linear fit is good*: R²≈1.0 on steady/degradation (errors
≤1.4%), but R² falls 1.00→0.79 across the saturating run and projection error rises
to 0.41–0.83. So the significant predictor is not velocity per se but **velocity
conditioned on fit quality (R²)**. `blocking_voids` direction is a clean
predictor of `DIVERGING` (degradation: voids rose 0→2, verdict DIVERGING from k=2).

**Q2 — when is linear sufficient.** Sufficient for locally-linear processes
(steady, monotonic decline: ≤1.4% error). **Insufficient for diminishing-returns /
saturating** processes — linear extrapolation keeps projecting the early slope and
overshoots by up to 83%. A non-linear (asymptotic / log) model is required there.

**Q3 — minimum history for HIGH confidence.** OLS slope standard error drops below
25% relative by **k=3** on every trajectory. But slope-stability does **not** imply
prediction accuracy: the noisy run has a "stable" slope yet a max window error of
0.46. ∴ the shipped rule (`confidence=LOW` iff <2 points) is **unjustified** —
confidence must be gated on fit quality (R²), not on point count alone.

**Q4 — does DIVERGING track reality.** Yes. On the only sign-flipping trajectory
(degradation), the verdict was DIVERGING in 100% of windows while measured mass
fell 30 555→7 535 and blocking_voids rose 0→2. The 1.00 overall rate is partly
inflated by sign-stable runs, but where direction actually changes, it is correct.

## Verdict

**The method is NOT falsified.** `expansion_verdict` has real *directional*
predictive power. The *magnitude* (`potential_mass`) meets the 0.15 criterion only
under local linearity (and, with OLS, under moderate noise); it **fails for
non-linear regimes**, where it must be treated as direction-only.

**Honest limitations found in the shipped v1.7.0 expander:**
1. two-endpoint velocity is strictly worse than OLS under noise (0.163 vs 0.131 —
   it *fails* the criterion where OLS passes);
2. `confidence` keyed on point-count is unjustified — it ignores fit quality;
3. nothing warns when the linear model is inappropriate (saturating), so
   `potential_mass` can be over-trusted by 40–80%.

These three findings are addressed in the evidence-driven upgrade (OLS slope,
R²-gated confidence, non-linearity warning) shipped alongside this study.
