# Day 8 — Science briefing: Minimum Detectable Change (MDC) and Q3

## 1. What Q3 asks

Q1 ranked configurations by accuracy; Q2 asked whether a fit-quality selector can
*pick* the accurate one. Q3 asks a different, decision-facing question: **given a
configuration's measured precision, what is the smallest change in I_D/I_G (and
therefore in defect density n_D) that this pipeline can actually resolve?** That
threshold is the **Minimum Detectable Change (MDC)**. It converts our error
characterization into the language an experimentalist uses: "you can trust a
difference only if it exceeds *this much*."

## 2. The MDC formula, term by term

```
MDC = (z_{1-alpha/2} + z_power) * sqrt(2) * sigma_single / sqrt(n_rep)
```

- **`z_{1-alpha/2}` (first z-value).** The two-sided critical value controlling
  the **false-positive** rate. At alpha = 0.05 it is `norm.ppf(0.975) ≈ 1.95996`.
  We split alpha across both tails because a "change" can be up or down.
- **`z_power` (second z-value).** The one-sided value giving the test its
  **power** (true-positive rate). At power = 0.8 it is `norm.ppf(0.8) ≈ 0.84162`.
  It buys the margin needed so a real change of size MDC is detected 80% of the
  time, not just 50%.
- **`sqrt(2)`.** A detectable *change* is a **difference of two independent
  measurements** (before vs after, sample vs reference). The variance of a
  difference of two independent draws each with variance σ² is 2σ², so its
  standard deviation carries a factor `sqrt(2)`.
- **`sigma_single`.** The **single-measurement precision** — the run-to-run
  spread of the estimate for one fixed configuration in one regime. In this
  project it is the sample sd (ddof=1) of the *signed* I_D/I_G error across the
  suite spectra of that (config, regime) cell.
- **`1/sqrt(n_rep)`.** Averaging `n_rep` independent replicates shrinks the
  precision of the mean by `1/sqrt(n_rep)`; at `n_rep = 4` the MDC halves.

Net reading: the two z-values set the statistical confidence/power budget,
`sqrt(2)` reflects that we detect *differences*, and the precision term is what
the pipeline actually delivers.

## 3. Why bias is reported SEPARATELY

`sigma_single` is **precision** (scatter); it says nothing about whether the
estimates are centered on the truth. A configuration can be very precise yet
systematically wrong. That systematic offset is **bias** = the *mean* signed
error. We report bias as its own number (`estimate_bias`) and never fold it into
the MDC, because they answer different questions: MDC = "what change can I
*resolve*?", bias = "how far off is my *zero point*?". A small MDC on top of a
large bias is precise-but-inaccurate, and silently combining them would hide
exactly that failure mode.

## 4. Δn_D: multiplicative propagation

The Cancado-2011 relation `n_D = [const / λ⁴] · (I_D/I_G)` is **linear and
multiplicative** in the ratio: a change of `MDC` in I_D/I_G maps to a change of
`C(λ) · MDC` in n_D, where `C(λ) = const / λ⁴`. Because the map is a pure
multiplication, propagating the **published constant uncertainty** is also
multiplicative: we carry a band `C_lo/C_central/C_hi = (const ∓/± uncertainty)/λ⁴`
and return `(C_central·MDC, C_lo·MDC, C_hi·MDC)`. The constant and its
uncertainty are READ from `calibrations.yaml` (1.8e22 ± 0.5e22 cm⁻² nm⁴); nothing
is hard-coded, and the function refuses to run if the uncertainty field is
missing rather than guessing it.

## 5. Naive vs protocol

- **NAIVE pipeline** = what a non-specialist would do by default: a `linear`
  baseline, a single `lorentzian` (no BWF G band), the minimal `DG` peak set, and
  the `height` intensity ratio.
- **PROTOCOL pipeline** = the *legitimately defensible* DG/area config — here, in
  each SNR regime, the DG/area configuration with the smallest signed-error sd.

The contrast is the deliverable: the protocol's smaller `sigma_single` yields a
smaller MDC, i.e. it can resolve finer defect-density changes. The pick is *not*
ad hoc: Day 6 established **peak set as the dominant accuracy driver** (DG ~5×
tighter than band-heavy sets), which is why the candidate pool is DG; and the
area definition / curved-baseline + voigt members are the accuracy-leading
families from that same ranking. Day 7's selector audit (Q2) and the T6b coverage
finding (nominal-95% intervals cover only 18–28% under realistic
misspecification) are why we do **not** claim the protocol gives honest 95%
intervals — MDC is a precision statement, not a coverage guarantee.

**FM5 illustrative caveat.** The naive-vs-protocol MDC numbers are an
**illustration** of the methodology on this synthetic disordered-carbon suite,
not a validated field protocol. They demonstrate *how* precision converts to a
detectable-change threshold; they are scoped to these spectra, configurations,
and SNR regimes, and the protocol row's stability is undefined because the Q1b
jackknife is vacuous (zero rank-eligible configs under the pre-registered
coverage floor).

## 6. How Day-6 and Day-7 findings define the legitimate pick

- **Day 6 (accuracy ranking):** peak set dominates accuracy; DG configs are ~5×
  more accurate than D′/D3/D4-heavy sets. → the protocol candidate pool is DG.
- **Day 6 (Gate V3):** the passing low-bias classes were all DG/area. → area is
  the defensible intensity definition for the protocol pool.
- **Day 7 (Q2 selector audit):** within a fixed peak set, fit quality tracks
  accuracy only weakly (and only at SNR15). → we cannot let a selector roam
  across peak sets to choose; we fix the pool to DG and pick on measured error sd.
- **Day 7 (T6b coverage):** standard intervals undercover badly under
  misspecification. → the protocol card reports MDC and bias as measured
  quantities, and flags coverage honestly rather than asserting 95% trust.
