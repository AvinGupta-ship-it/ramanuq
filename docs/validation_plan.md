# Validation Plan

**Pre-registration document**
**Date:** 2026-06-15
**Author:** Avin Gupta
**Status:** FROZEN

This document is pre-registered and frozen. Tolerances and definitions below are
fixed prior to running the corresponding code and must not be changed after the
fact.

## Section 1 — Validation Gates

- **V1 — Parameter recovery:** Recovered parameters must agree with the known
  generating parameters within **0.1% relative**.
- **V1b — Empirical coverage:** Empirical 95% coverage must fall within the
  range **0.90 to 0.98**.
- **V2 — Baseline fit:** Baseline RMS error must be **below 2% of G-band
  height**.
- **V3 — Hostile-spectrum bias:** At least one configuration class must achieve
  **mean absolute bias below 5%** on stage-1 hostile spectra at **SNR 50**.
- **V4 — Selector sanity:** **Exact recovery** is required on rigged selector
  cases.
- **V5 — Published-spectrum reproduction:** At least **one digitized published
  spectrum** must be reproduced within **±10%**.
- **V6 — Cross-implementation agreement:** Independent implementations must agree
  within **1e-9 relative (analytic)** or **1e-6 relative (numerical)**.

## Section 2 — Operational Ground-Truth Definition

True band intensities are defined as coming from the generator's noiseless,
baseline-free band functions. True area is defined as the integral of the band
function, and true height is defined as the maximum of the band function. Both
the true area and the true height are stored per spectrum.

## Section 3 — Q1 Ranking Rule and Q1b Jackknife

- **Q1 ranking rule:** [ranking rule to be specified]
- **Q1b jackknife:** [jackknife procedure to be specified]

## Section 4 — Q2 Metrics

- **Metrics:** Spearman rank correlation, top-1 regret, and top-quartile
  probability.
- **Evaluation scopes:** Computed both full-grid and within-peak-set.
- **Uncertainty:** Bootstrap confidence intervals over spectra.

## Section 5 — Q2 Prediction (T1.6)

Prediction registered 2026-06-15, before any selector code exists. I predict H_C (mixed), specifically that fit quality and I_D/I_G accuracy will be decoupled across different peak sets but loosely correlated within one fixed set. Practically: if you let the model pick from many different peak configurations, the best-scoring one often isn't the most accurate (high regret); but if all candidates share the same peaks, the best-scoring one usually is close to accurate (low regret). I expect the within-set correlation to be positive but weak, and weakest for messy spectra like hydrogenated SWCNTs and rGO.
