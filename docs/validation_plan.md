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
  - **V2 pairing clarification (Avin Gupta, 2026-06-18):** The 2% tolerance is
    applied in-class — each baseline method is graded only on backgrounds it is
    designed to represent. `linear` is tested on `none` only (a straight line
    cannot represent a curved background, so grading it on `mild_cubic` or
    `strong_curved` measures the estimator's mathematical limitation, not
    baseline-layer correctness). `poly3`, `poly5`, and `als` are curved-baseline
    estimators and are tested on all three severities (`none`, `mild_cubic`,
    `strong_curved`), including severe curvature. The 2% threshold itself is
    unchanged from pre-registration; this note fixes only the method→baseline
    scope, which the original entry left unspecified.
- **V3 — Hostile-spectrum bias:** At least one configuration class must achieve
  **mean absolute bias below 5%** on stage-1 hostile spectra at **SNR 50**.
- **V4 — Selector sanity:** **Exact recovery** is required on rigged selector
  cases.
  V4 — measured Day 7: GREEN. Rigged correlated frame recovered ρ = +1.0, regret = 0.0;
anti-correlated frame recovered ρ = −1.0. Exact recovery at atol = 1e-12. (3 V4 tests
pass in tests/test_selectors.py.)
- **V5 — Published-spectrum reproduction:** At least **one digitized published
  spectrum** must be reproduced within **±10%**.
  Gate V5 (demonstration, ±10%): Cançado-2011 L_D=7 nm spectrum, published I_D/I_G = 1.6, height mode, config linear/lorentzian/DG/height (baseline = documented free variable, set to the simplest defensible linear baseline a priori, not tuned to pass). Measured I_D/I_G = 1.5227 — PASS within ±10% (window 1.44–1.76). Recorded Day 10, June 24 2026.
- **V6 — Cross-implementation agreement:** Independent implementations must agree
  within **1e-9 relative (analytic)** or **1e-6 relative (numerical)**.
  V6 (metrics) — Day 5 result 6/19/2026: GREEN. metrics.py vs clean-room refimpl/ref_metrics.py
agree on 1500 randomized cases — ratios rtol<1e-9, La/n_D/const-uncertainty rtol<1e-6, stage-guard
boolean+reasons exact. Constants load identically from calibrations.yaml on both sides.
Hand-pin #2 (mine): La=19.2246 nm, n_D=2.2471e11 cm^-2 at 532 nm, I_D/I_G=1.0 — metrics.py matches.
Tier-1 L3 read complete, verdict Y. Found + fixed a latent area/height routing bug (prose word-order
classifier replaced with explicit intensity_kind field). Stage guard fires on stage-2 (G FWHM>40 cm^-1
or D3/G>0.15), NaNs calibrated quantities + flag + warning, id_ig stays valid; no false-fire on stage-1. <commit:dd89103a2cae541d39b91e77f731724da1171eca>
  V6 (selectors) — measured Day 7: GREEN. selectors.py agrees with the blind clean-room
refimpl/ref_selectors.py on ρ and top1_regret across randomized frames to <1e-6
(tests/test_differential_v6.py::test_selectors_match_reference). Reference authored in
an isolated sibling folder with no source present (provable blindness).

### 2026-06-22 — Day 8 (MDC / Q3) results.
Gate V6 extended to mdc: ref_mdc/mdc and ref_to_delta_nd/to_delta_nd agree
  to <1e-9 on randomized inputs (CI). PASSED.
Hand-pin #3: sigma_single=0.10, alpha=0.05, power=0.8, n_rep=1 -> MDC=0.396203
  in I_D/I_G; code reproduces it (test_hand_pin_mdc_idig PASSED).
T7 MDC (naive [linear/lorentzian/DG/height] vs protocol [smallest-error-sd DG/area]):
  SNR15:  naive 0.745  protocol 0.529  (Delta_nD central 1.19e11 cm^-2)  [poly5/gaussian]
  SNR50:  naive 0.763  protocol 0.271  (Delta_nD central 6.08e10 cm^-2)  [als/pseudo_voigt]
  SNR200: naive 0.703  protocol 0.565  (Delta_nD central 1.27e11 cm^-2)  [als/pseudo_voigt]
  Naive requires ~1.4x / 2.8x / 1.2x larger change to detect, by regime.
Protocol recommendations authored same date in protocol.md; grounded in measured
  accuracy ranking + honest-coverage finding (no config reached 0.90 floor; max 0.467).
CX-1 review of mdc.py: 0 blockers / 1 deferred NIT (unused schema tuples).

### Day 6 — measured results (Tier-B grid study, 2026-06-21)
Study: 96 configs × 90 Tier-B spectra = 8640 rows, n_boot=40. Commit: <Fd6cf19b>.

- **Gate V3 — measured: PASS.** stage1/SNR50 slice: 9 of 72 (lineshape,baseline,peak_set,intensity)
  classes achieve mean |bias| < 0.05 (tolerance unchanged). All passing classes are DG/area.
  Best: pseudo_voigt·poly5·DG·area, mean |bias| = 0.0052.
- **Q1 ranking — EMPTY (the headline finding).** Under the pre-registered rule (RMSE ascending,
  subject to coverage ≥ 0.90 and failure ≤ 0.05), NO configuration is rank-eligible in any SNR
  regime. Maximum empirical 95% coverage across all 216 (config × SNR) cells is 0.80; zero cells
  reach the 0.90 floor. This is the expected manifestation of FM4: statistical-only bootstrap
  intervals undercover under out-of-family misspecification, so no standard configuration produces
  honest 95% intervals on hostile data. The rule and floor were NOT changed to force a result.
- **Q1b stability — vacuous.** With no rank-1 configuration in any regime, the jackknife has no
  recommended config to test: 0 recommended configs, 0 flip flags, no retention/IQR. Rank stability
  is undefined (not "stable").
- **Failure rate — reported (FM1).** 25% of rows per peak set are non-finite id_ig, driven entirely
  by bwf_g=True (BWF G-band yields NaN id_ig on non-Fano stage-1 spectra, by design) plus the
  stage-2 stage-guarded rows. Not hidden; reported as data.
- **Descriptive spread (NOT causal):** sigma_meth rises with baseline severity (none 1.01 → mild
  1.20 → strong 1.50). DG peak set ~5× tighter in mean |error| than any D′-containing set. Marginals
  are confounded by the factorial layout; not read as main effects.
- **Spot-recompute (human, Avin):** verified row als·pseudo_voigt·DG·area on tierB_stage1_blmild_snr50_i3:
  id_ig 0.99860, true_id_ig_area 0.98808 (area config correctly joined AREA truth, not height 2.031),
  error +0.01052 = id_ig − true_id_ig. ✓

### Gate V1 — measured result (Day 3)
- Pre-registered tolerance (UNCHANGED): < 0.1% relative recovery error, every stage-1 noise-free, baseline-free matched-recovery case (both area and height truth definitions).
- Execution date: 2026-06-18
- Commit: 1ec1b4a
- Cases tested: 4 stage-1 noise-free, baseline-free matched-recovery cases (ratios 0.1, 0.5, 1.0, 2.0). Stage-2 excluded — see scope note below.
- Maximum relative error: 0.000008% (case: tierA_stage1_r0p5_recovery, area definition)
- Status: PASS
- Stage-2 scope note: stage-2 is excluded from V1's strict bound because its truth mixes Lorentzian D/G with Gaussian D3/D4, while fit_spectrum applies a single lineshape to all bands — so no matched PipelineConfig exists. Documented residual (~41%) recorded in test_v1_stage2_excluded_with_documented_residual.
### Gate V2 — measured result (Day 4)
- Pre-registered tolerance (UNCHANGED): baseline RMS error < 2% of reference G-band height, per method, on peak-free Tier-A baselines.
- Pairing (per the 2026-06-18 in-class clarification above): linear tested on `none` only; poly3, poly5, als tested on `none`, `mild_cubic`, and `strong_curved`. 10 in-class (method, baseline) pairs total.
- Measured: all 10 in-class pairs < 2% of reference G height. Worst case: poly3 on `strong_curved` = 1.97% (PASS, tight). poly5 and als pass on all three severities; linear passes on `none`.
- Status: PASS
- Detail: tests/test_baseline.py (@pytest.mark.validation), commit [eo7ced4].

### Day 4 — additional measured results (Tier-B hostile suite)
- Tier-B suite: 90 spectra (2 stages × 3 baseline severities × 3 SNR × 5 instances), each with paired CSV + both-definition truth JSON. 90/90 pairing, no orphans.
- Non-Lorentzianity (out-of-family proof): best independent single-Lorentzian fit leaves relative RMS residual > 1% on every band. Measured: composite D 5.1%–53.3%, EMG G 15.6%–21.7% — gate cleared by >5× worst case. Status: PASS.
- Determinism: all 90 cases reproduce bit-for-bit (same case_id + seed → identical CSV + truth); confirmed by full 90-case regeneration cross-check in CX-3 review. Status: PASS.
- Tier-B realism eyeball gate (human, Avin Gupta): PASS — four representative spectra judged visibly non-Lorentzian yet realistic, consistent with real disordered-carbon spectra. Recorded in docs/tierB_realism_gate.md.
- CX-3 numerical edge-case review: 0 blockers, 2 recorded NITs (pre-existing design consequences). Recorded in docs/cx3_review_day4.md.
- Detail: tests/test_fit_recovery.py (@pytest.mark.validation); verified live via matched-config readout on 2026-06-18.

### T6 — Selector audit (Day 7), synthetic_disordered_carbon, 30 spectra/cell, ρ = median
per-spectrum Spearman with 95% spectrum-level bootstrap CI:
- Full stratum: all ρ medians within ±0.08 of zero (range −0.079 to +0.063); CI clears
  zero in 4/9 cells; established redchi cells lean negative.
- Within_peak_set: ρ positive in all 9 cells; CI clears zero only at SNR15
  (aic +0.094 [+0.024,+0.160]; bic +0.084 [+0.023,+0.180]; redchi +0.081 [+0.024,+0.165]);
  SNR50/200 straddle zero.
- Regret: full 2–3× within at every SNR (SNR15 1.37 vs ~0.44; SNR50 0.55–0.67 vs 0.28–0.34;
  SNR200 0.88 vs 0.38–0.42).
Full per-cell table (incl. all CIs and hit rates) regenerated by ramanuq.selectors.audit()
on data/synthetic/results/tierB_grid_results.parquet; rendered in notebooks/03_selector_q2.

### T6b — Coverage under misspecification (Day 7), pooled over all grid configs per regime, - commit: 0fb6ff0baedef3ba790603f883e621a33021c040
inclusive endpoints:
  SNR 15:  coverage 0.276 (n=2160)
  SNR 50:  coverage 0.240 (n=2160)
  SNR 200: coverage 0.183 (n=2160)
Nominal intervals are 95%; measured coverage 18–28% — standard residual-bootstrap intervals
undercover under realistic misspecification (FM4). Pooled-config definition is the ratified
T6b convention (see note below).

## Section 2 — Operational Ground-Truth Definition

True band intensities are defined as coming from the generator's noiseless,
baseline-free band functions. True area is defined as the integral of the band
function, and true height is defined as the maximum of the band function. Both
the true area and the true height are stored per spectrum.

## Section 3 — Q1 Ranking Rule and Q1b Jackknife

- **Q1 ranking rule:** Within each (material class, SNR regime), configurations
  are ranked by **RMSE of I_D/I_G error against truth, ascending** (lowest RMSE =
  best). A configuration is **rank-eligible only if** its empirical 95% coverage
  is **≥ 0.90** (the V1b lower bound) **and** its failure rate is **≤ 5%**.
  Configurations failing either floor are excluded from the ranking, not ranked
  last. RMSE is the ordering metric; coverage and failure are eligibility gates.
  (Coverage floor 0.90 chosen to match the pre-registered V1b coverage band
  0.90–0.98, so the same honesty bound governs rank-eligibility.)
- **Q1b jackknife:** The per-regime ranking is recomputed under leave-one-out
  jackknife over two unit types: **(a) configuration families** — drop each
  baseline class, each lineshape, and each peak set in turn — and **(b) suite
  instances** — drop each random instance within a cell in turn. For the
  protocol-recommended configuration, report per regime: **top-quartile retention
  frequency** (fraction of resamples in which it remains in the top quartile),
  **rank IQR** (interquartile range of its rank across resamples), and a **flip
  flag** for any regime where the recommendation changes. Allowed claim form: the
  recommended config was rank-stable in regimes where it stayed top-quartile in
  ≥ N% of resamples, and unstable (flagged) elsewhere.

## Section 4 — Q2 Metrics

- **Metrics:** Spearman rank correlation, top-1 regret, and top-quartile
  probability.
- **Evaluation scopes:** Computed both full-grid and within-peak-set.
- **Uncertainty:** Bootstrap confidence intervals over spectra.

## Section 5 — Q2 Prediction (T1.6)

Prediction registered 2026-06-15, before any selector code exists. I predict H_C (mixed), specifically that fit quality and I_D/I_G accuracy will be decoupled across different peak sets but loosely correlated within one fixed set. Practically: if you let the model pick from many different peak configurations, the best-scoring one often isn't the most accurate (high regret); but if all candidates share the same peaks, the best-scoring one usually is close to accurate (low regret). I expect the within-set correlation to be positive but weak, and weakest for messy spectra like hydrogenated SWCNTs and rGO.

## Q2 Verdict — Selector Audit (Day 7)

**Prediction (Section 5, registered 2026-06-15, verbatim):**
"I predict H_C (mixed), specifically that fit quality and I_D/I_G accuracy will be
decoupled across different peak sets but loosely correlated within one fixed set.
Practically: if you let the model pick from many different peak configurations, the
best-scoring one often isn't the most accurate (high regret); but if all candidates
share the same peaks, the best-scoring one usually is close to accurate (low regret).
I expect the within-set correlation to be positive but weak, and weakest for messy
spectra like hydrogenated SWCNTs and rGO."

**Result** (synthetic_disordered_carbon suite, 30 spectra/cell; ρ = median per-spectrum
Spearman, 95% spectrum-level bootstrap CI; regret in I_D/I_G units):
- Full-stratum ρ: all medians within ±0.08 of zero (range −0.079 to +0.063); CI clears
  zero in 4 of 9 cells (bic SNR15 +0.046 [+0.006,+0.078]; redchi SNR15 −0.079
  [−0.142,−0.014]; redchi SNR200 −0.077 [−0.144,−0.001]; aic SNR200 −0.052
  [−0.132,−0.001]) — the established ones for redchi lean negative.
- Within-peak-set ρ: positive in all 9 cells; CI clears zero in only 3 (all SNR15:
  aic +0.094 [+0.024,+0.160], bic +0.084 [+0.023,+0.180], redchi +0.081
  [+0.024,+0.165]); the other 6 (SNR50, SNR200) straddle zero.
- Regret: full-stratum 2–3× within-stratum at every SNR (SNR15: 1.37 vs ~0.44;
  SNR50: 0.55–0.67 vs 0.28–0.34; SNR200: 0.88 vs 0.38–0.42).
- T6b coverage under misspecification: 0.276 / 0.240 / 0.183 at SNR 15 / 50 / 200.

**Sub-claim 1 — decoupling across peak sets (full grid):** Predicted full-stratum ρ near
zero and high regret. ρ near zero with mostly straddling CIs, but 4 cells clear zero
(decoupling holds for most, not all cells). Full regret is 2–3× within regret at every
SNR (the high-regret prediction holds). → **PARTIALLY CONFIRMED** (regret contrast strong;
ρ near-zero but a few faint effects, redchi leaning slightly negative).

**Sub-claim 2 — coupling within a fixed peak set:** Predicted within-set ρ positive and
low regret. Median ρ positive in all 9 cells, but the CI clears zero in only 3 (all at
SNR15); the other 6 straddle zero, so coupling is established only for the noisiest
spectra and not statistically established at SNR50/200. Within regret is the low side of
the contrast (2–3× below full). → **PARTIALLY CONFIRMED** (real positive coupling at SNR15;
positive-but-not-established at higher SNR).

**Sub-claim 3 — within-set correlation positive but weak:** Predicted small positive
within-set ρ. The established within-set ρ's are +0.08 to +0.09 — positive and genuinely
tiny, exactly as predicted; at SNR50/200 the effect is even weaker (positive but not
established). → **CONFIRMED** (if anything, weaker than predicted at higher SNR).

**Sub-claim 4 — weakest for messy spectra (hydrogenated SWCNTs, rGO):** This suite has a
single material_class (synthetic_disordered_carbon) and no material-class axis, so the
prediction as written is UNTESTABLE here. Using SNR as a noise/messiness proxy, within-set
coupling was *strongest* (and only established) at the noisiest SNR15 and washed out at the
cleanest SNR200 — the opposite direction. → **UNTESTABLE AS WRITTEN; REFUTED VIA SNR PROXY.**
Flagged for future work with a multi-material suite.

**Overall verdict: PARTIALLY CONFIRMED.** The central structural prediction — accuracy
decoupled across peak sets, coupled within a fixed set — broadly held: the full grid is
near-decoupled with 2–3× higher regret, and within-set correlation is positive with lower
regret. But the within-set coupling is statistically established only for the noisiest
(SNR15) spectra, and the specific claim that messy spectra would show the weakest coupling
was untestable as written and ran backwards under an SNR proxy.

**Mechanism:** Day-6 established peak set as the dominant accuracy driver (DG configs ~5×
more accurate than band-heavy sets). Within a fixed peak set, only baseline/lineshape/
intensity vary, and these move accuracy little — leaving a small accuracy signal for fit
quality to track (the weak positive within-set ρ). Across peak sets, the selector can swing
between DG and overfitting band-heavy sets, producing the high full-grid regret.

**Headline result:** The practically important finding is not in ρ but in T6b: the typical
configuration's nominal 95% interval contains the truth only 18–28% of the time across SNR
regimes — reported error bars are not honest 95% intervals under realistic misspecification
(the expected FM4 outcome, elevated to a headline).

**Scope:** Holds on the spectra, configurations, and SNR regimes of the synthetic
disordered-carbon suite tested here.

— Avin Gupta, 2026-06-22

## Day 9 - 2026-06-24 ##
report_data.json populated from the Day-6 study parquet + recorded results; key cited numbers verified by me to match my authored protocol.md: protocol MDC 0.529/0.271/0.565 and naive MDC 0.745/0.763/0.703 (SNR 15/50/200); T6b coverage 0.276/0.240/0.183; Gate V3 best class pseudo_voigt/poly5/DG/area = 0.0052; Q1 ranking empty (max coverage 0.80 < 0.90 floor; 0 rank-eligible configs). Figures F1–F9 generated via viz.py; figure_qa harness GREEN on all nine; byte-identical across two renders (deterministic: Agg backend, fixed SEED, no timestamps). 15-minute scientific figure pass DONE by me; every figure consistent with recorded findings (F3/F4 DG/area accurate + bands overfit + coverage below floor everywhere; F5 selector ρ≈0 + T6b undercoverage 0.276/0.240/0.183; F6/F7 match my authored protocol numbers; F8 shows the three selected demonstration spectra; F9 honest empty rank-stability). CX-1 code review: 0 BLOCKERS / 4 NITS (deferred to Day-14 cosmetic pass). Vision-rubric review: F3 label overlap + F1(b) crowding deferred to Day 14; F7 x-axis tick fix applied today (byte-identity preserved). Demonstration spectra selected (my literature judgment): (1) Cançado et al. 2011, Nano Lett. 11, 3190, Fig 1, L_D=7nm spectrum — method-stating (height), Gate-V5 anchor, published I_D/I_G=1.6, 514.5 nm, stage-1; (2) N-rGO, arXiv:1902.01850, Fig 5, published I_D/I_G=1.14 (height), 532 nm; (3) fCNT, arXiv:1711.01957, Fig 1a, published I_D/I_G=1.64 (area), 514.5 nm. Digitization complete and verified by me (10 random points + both axis calibrations per spectrum; V5 spectrum twice-digitized, two height-ratios 1.721/1.691 agree within 1.7%). provenance.yaml fields confirmed by me. Gate V5 staged for Day 10 (per §9.10 / §8.2 / P11: V5 asserted in notebook 04 on Day 10; ±10% tolerance, demonstration-only). Digitization + provenance done today. Note: paper defines I_D/I_G as height ratio but does not pin. Day-9 work commit: 6f05111 

## DAY 10 - 2026-06-24 ##
Day 10: report PDF built via number injection — all 80 reported numerals resolved from report_data.json; grep confirmed no stray hand-typed result numbers. All interpretive prose (abstract, Q1/Q1b/Q2/Q3, limitations) and the disclosure checklist authored by me; Q2 verdict included verbatim from Day-7. CX-5 prose-critique flags all resolved by me, including softening the §4 peak-set language from causal to descriptive to match the pre-registration's "NOT causal" marking.