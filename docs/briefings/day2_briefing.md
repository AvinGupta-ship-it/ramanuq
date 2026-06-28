# RamanUQ — Day 2 Science Briefing

Audience: project newcomers. Goal: understand the pieces of the spectral
analysis pipeline implemented today, and why each step exists.

---

## 1. Line shapes (how a single peak is modeled)

A Raman band is modeled as a parametric peak. We use three families:

- **Lorentzian** — heavy tails; typical of lifetime-broadened modes. Defined so
  its integral over the whole axis equals the `area` parameter. Height at center
  is `2*area/(pi*FWHM)`.
- **Gaussian** — light tails; typical of inhomogeneous broadening. Also
  area-parameterized; height at center is `area/(sigma*sqrt(2*pi))` with
  `sigma = FWHM / (2*sqrt(2*ln2))`.
- **Pseudo-Voigt** — a linear blend `eta*Lorentzian + (1-eta)*Gaussian` sharing
  one `area` and one `FWHM`. `eta` in `[0,1]`: `eta=1` is pure Lorentzian,
  `eta=0` is pure Gaussian. Because both components carry the full `area`, the
  blend's total area is exactly `area`.

We deliberately parameterize by **area**, not height, because area is the
physically conserved, additive quantity when bands overlap.

**BWF (Breit-Wigner-Fano)** is the exception: an *asymmetric* profile used for
the G band of carbons. It is **height-parameterized** (`height` = value at
center) with an asymmetry parameter `q`; as `|q| -> infinity` it tends to a
Lorentzian. Its infinite-axis integral does not converge, so there is no
closed-form "area" for it — an important caveat when comparing intensities.

Analytic `height <-> area <-> FWHM` helpers let us convert between
parameterizations exactly (round-trips recover to ~1e-6 or better).

## 2. Baseline (removing the background)

Real spectra sit on a slowly varying background (fluorescence, detector
offset). We estimate and subtract it. Methods:

- **linear / poly3 / poly5** — least-squares polynomials of degree 1/3/5.
  Simple, but can be pulled by strong peaks.
- **ALS (asymmetric least squares, Eilers-Boelens)** — iteratively reweighted
  smoothing that penalizes curvature (`lam`, default 1e5) and asymmetrically
  weights points above vs. below the current estimate (`p`, default 0.01), so
  the baseline hugs the valleys and ignores peak tops.

Baseline choice is a known source of analysis variability — different operators
pick different methods, which is exactly why the pipeline treats it as a
configurable knob.

## 3. Despiking (removing cosmic rays)

A cosmic ray hits one or two detector channels and produces a huge, narrow
spike that is *not* a real band. We remove it with a **rolling-median z-score**:
compute a local median, take each channel's residual from it, scale by a robust
(MAD-based) sigma, and replace channels whose z-score exceeds a threshold with
the local median.

Why this works: real Raman bands are broad, and on their monotonic flanks the
center sample *is* the local median, so the residual is ~0 — they survive. A
single-channel spike leaves the median untouched and stands out strongly.
Replacing spikes with the local median makes the despiker **idempotent**:
running it twice gives the same result as running it once.

## 4. Fitting (estimating the parameters)

`fit_spectrum` runs the pipeline end to end:

1. **Despike** the raw intensity.
2. **Subtract the baseline.**
3. **Bounded weighted least squares (WLS).** Peaks are summed into a composite
   model with physically sensible bounds (centers within +/-40 of their band
   anchor, FWHM in [4,300] — tighter [4,60] for the narrow D-prime band, areas
   >= 0). Initial guesses come from **windowed maxima** (the largest value near
   each band's anchor seeds its center and amplitude). Intensity is **rescaled
   to O(1)** before fitting for numerical conditioning, then converted back.
4. **Per-fit diagnostics:** reduced chi-square (`redchi`), `aic`, `bic`.

The pipeline **never raises on non-convergence** — a failed fit is *recorded*
(NaN stats, `success=False`), not thrown. This matters because we run the
pipeline across many configurations and must not lose a whole run to one bad
fit.

## 5. Residual bootstrap (where the uncertainty comes from)

To get parameter uncertainties without assuming a noise distribution, we use a
**residual bootstrap on the fitted residuals**:

1. Fit once; compute residuals `r = data - model`.
2. Resample `r` with replacement and add it back to the fitted model to make a
   synthetic dataset.
3. Refit. Repeat (default 200 times).
4. Summarize each parameter's bootstrap distribution with **percentile
   intervals** (e.g., 2.5%–97.5%).

Refits that fail to converge are **counted** (`n_failed`) rather than allowed to
crash the run — so the reported intervals are honest about how many resamples
succeeded.

## 6. AIC / BIC (comparing models of different complexity)

When we fit more bands (DG vs. DGDp vs. DGDpD3D4), residuals always shrink, so
raw goodness-of-fit cannot tell us whether the extra bands are justified.
Information criteria penalize complexity:

- `aic(n, k, rss) = n*ln(rss/n) + 2k`
- `bic(n, k, rss) = n*ln(rss/n) + k*ln(n)`

`n` = number of points, `k` = number of free parameters, `rss` = residual sum
of squares, and `ln` is the **natural** log. Lower is better. BIC penalizes
extra parameters more heavily than AIC for realistic `n` (since `ln(n) > 2`),
so it prefers simpler models. These are standalone, importable functions so they
can be checked independently.

## 7. Gate V6 (the differential-testing gate)

Gate V6 is a correctness gate based on **differential testing**. A separate
**clean-room** session writes an independent reference implementation (under
`refimpl/`) and a comparison test (`tests/test_differential_v6.py`). The gate
passes only when the working implementation and the independent reference
**agree within tolerance** on the shared, exactly-specified functions (e.g., the
line shapes and the AIC/BIC formulas).

Why it matters: two people implementing the same fixed contract independently
are unlikely to make the *same* mistake. Agreement between them is strong
evidence the math is right; disagreement localizes a bug. This is why the public
API (function names, argument orders, formulas) is pinned exactly — so the two
implementations are directly comparable.

---

# Day 2 Quiz (3 questions)

**Q1 — Line shapes.** A pseudo-Voigt is `eta*Lorentzian + (1-eta)*Gaussian` with
both components sharing the same `area` and `FWHM`. (a) What is the total
integrated area of the blend, and why? (b) What does `eta = 1` reduce to?
(c) Why does the BWF profile have no closed-form area?

**Q2 — Despiking & bootstrap.** (a) Explain why a broad real Raman band survives
a rolling-median despiker while a single-channel cosmic-ray spike is removed.
(b) In the residual bootstrap, what exactly is resampled, and what does
`n_failed` count?

**Q3 — Model selection.** Adding more bands always lowers the residual sum of
squares. (a) Write the AIC and BIC formulas (state the base of the logarithm).
(b) For a fixed fit, which one more strongly penalizes extra parameters once
`n > 7`, and why? (c) In one sentence, what does Gate V6 verify and how?

---

## Answer key

**A1.** (a) Exactly `area`, because each component is individually normalized to
`area`, so `eta*area + (1-eta)*area = area`. (b) A pure Lorentzian
(`eta=0` is pure Gaussian). (c) Its tails fall off too slowly — the
infinite-axis integral diverges — so it is parameterized by height, not area.

**A2.** (a) On a broad band's monotonic flanks the center sample is the local
median, so its residual is ~0; a one-channel spike doesn't move the median and
produces a large robust z-score. (b) The *fitted residuals* (`data - model`) are
resampled with replacement and added back to the fitted model; `n_failed` counts
bootstrap refits that did not converge.

**A3.** (a) `AIC = n*ln(rss/n) + 2k`, `BIC = n*ln(rss/n) + k*ln(n)`, natural log.
(b) BIC, because its per-parameter penalty `ln(n)` exceeds AIC's `2` once
`n > e^2 ≈ 7.4`. (c) Gate V6 checks that an independent clean-room reference
implementation agrees with the working code within tolerance on the shared
exactly-specified functions (via a differential test).
