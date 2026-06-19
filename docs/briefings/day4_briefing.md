# Day 4 Science Briefing — Tier-B Hostile Spectra & Gate V2

**Date:** 2026-06-18 · **Topic:** out-of-family truth, smooth random baselines,
and the baseline-fit gate

## Why "hostile" spectra
Tier A asked: given the *right* model form, does the pipeline recover the truth?
That is necessary but easy — the fitter and the generator agree on the band shape.
Real disordered-carbon spectra do **not** oblige. Their bands are not single
Lorentzians, their backgrounds wander, and the analyst's model is therefore
*misspecified*. Tier B (the "hostile" suite) deliberately builds spectra the
fitter **cannot** represent exactly, so we can later measure how wrong I_D/I_G
gets when the model is wrong — separately from noise and from baseline removal.

## Hostile truth: same rule, no closed form
The pre-registered truth rule is unchanged (validation_plan.md §2): true band
**area** is the integral of the noiseless, baseline-free band function; true band
**height** is its maximum; both are stored, labelled `true_id_ig_area` and
`true_id_ig_height`. The only difference from Tier A is mechanical: the Tier-B
band functions have no closed-form integral, so the area truth is the **numeric
integral (trapezoid) of the band callable** over the spectrum grid, and the height
truth is `max(callable)`. Truth is still computed **before** baseline and noise
are added, and is **never** read back off the observed (baseline+noise) curve.

## Out-of-family band shapes
- **Composite band** — a sum of 3–7 jittered narrow Lorentzians. The *aggregate*
  is not a Lorentzian (this mimics inhomogeneous broadening: many slightly
  different micro-environments). Crucially, the band **height** truth is the max
  of the *summed* callable, **not** the sum of the sub-peak heights — overlapping
  sub-peaks never simply add to their individual maxima.
- **EMG band** — a Gaussian core convolved with a one-sided exponential of
  time-constant `tau`, producing an asymmetric tail. Real bands are often
  asymmetric; a symmetric Lorentzian/Gaussian/pseudo-Voigt cannot match this.
- **Mixed-Voigt band** — a pseudo-Voigt with a *per-band* Lorentzian/Gaussian
  mixing fraction `eta`, so different bands blend differently and no single fixed
  lineshape choice is right for all of them at once.

## Smooth random baselines (NOT a Gaussian process)
The background is `gp_baseline(severity, seed)` = **a sum of broad random
Gaussians plus a decaying exponential**, at severities `none|mild|strong`. The
name "gp_baseline" is a **label only**: it is *not* a Gaussian-process regressor
and imports no GP/sklearn library. It produces smooth, sample-varying backgrounds
(like fluorescence + instrument drift) without ever touching the true band
parameters, so the truth stays clean.

## Proving "out of family" — without claiming realism
We must not over-claim that these spectra are physically realistic. What we *can*
prove rigorously is that they are **outside the single-Lorentzian family** the
fitter assumes: for each composite and EMG band we fit the **best independent
single Lorentzian** (a real least-squares fit, not a comparison of the band to
itself) and require the relative RMS residual to exceed **1%**. Measured margins
are ≈5% (composite) and ≈16% (EMG) — comfortably out of family. This is a
statement about model class, not about physical fidelity.

## Determinism and "both definitions, always"
A single project `SEED` feeds all randomness; each case derives its draws from
`SeedSequence([SEED, crc32(case_id)])`, so the 90 cases are mutually independent
yet each is bit-for-bit reproducible. Every truth record stores **both** the area
ratio and the height ratio (they differ by the band-width factors and a bare
"intensity" is ambiguous), plus every generator parameter, the baseline metadata
and severity, the seed, and the generator-family labels.

## Gate V2 — the baseline-fit gate
Pre-registered V2: baseline RMS error must be **below 2% of the G-band height**
(tolerance frozen). We test it on the explicitly-allowed **peak-free** truth
construction — a noiseless spectrum that is *only* the Tier-A baseline curve — so
we measure the baseline estimator's quality in isolation, with no peaks to
confound it and no truth information a real analysis wouldn't have. Per the
in-class pairing recorded in `validation_plan.md`, each method is graded only on
backgrounds it can represent: `linear` on `none` only (a straight line provably
cannot fit a curved background — grading it there would measure a known
mathematical limit, not baseline-layer correctness), while the curved-baseline
estimators `poly3`, `poly5`, and `als` are graded on all three severities,
including severe curvature.

## The human Tier-B realism eyeball gate
Statistics prove "out of family" but not "looks like a real spectrum." That
judgement is reserved for a human: four representative Tier-B figures (varying
stage, baseline severity, and SNR) plot the observed spectrum, the baseline-free
band components, and the added baseline. The implementer produces the figures and
makes **no** realism judgement — a person inspects them and decides whether the
hostile suite is plausible enough to stress the pipeline honestly.

---

## Quiz (no answers shown)

1. For the composite (multi-Lorentzian) band, we define the true band **height**
   as the maximum of the summed callable, not the sum of the sub-peak heights.
   Explain why those two numbers differ, and what specific error in I_D/I_G(height)
   you would introduce by using the sum instead.

2. `gp_baseline` is named after a Gaussian process but is implemented as "broad
   random Gaussians plus a decaying exponential," with no GP library. (a) State
   what it actually computes. (b) Explain why the out-of-family proof and the V2
   baseline gate would each be undermined if truth were instead read off the
   observed (baseline+noise) spectrum.

3. Gate V2 grades `linear` only on the `none` baseline, but grades `poly3`,
   `poly5`, and `als` on `strong_curved` as well. Justify this in-class pairing in
   terms of what the 2% gate is actually meant to certify, and explain why grading
   `linear` on `strong_curved` would *not* be a fair test of the baseline layer.
