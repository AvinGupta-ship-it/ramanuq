# Tier-1 L3 Read — selectors.py (Day 7)

**Module:** `src/ramanuq/selectors.py`
**Reader:** Avin Gupta
**Date:** 2026-06-22
**Spec read against:** Execution manual prompt P8 / Part VII (Q2 selector audit);
validation_plan.md Section 4 (Q2 metrics & strata). Section 5 (my Q2 prediction)
NOT consulted for this read.

This is the third and final Tier-1 module (after hostile.py truth-definition and
metrics.py calibration wiring). It is in the irreducible reading core because the
statistics are self-confirming: the module passed Gate V4 (exact recovery) and
Gate V6 (agreement with the blind clean-room ref_selectors.py), but neither gate
proves the *shared convention* is the one I pre-registered — only that the two
implementations agree. This read confirms the conventions against the spec by
tracing one spectrum by hand through the actual functions.

---

## Worked trace — one spectrum, six configs

case_id = tierB_stage1_blmild_snr50_i3, material_class = "stage1", snr_label = 50.
Six configs spanning two peak sets, built to show the Day-6 mechanism: the 5-band
configs fit better (lower redchi) but are less accurate (higher abs_error); AIC
penalizes their extra parameters.

| config | peak_set   | redchi |  aic | abs_error |
|--------|------------|--------|------|-----------|
| A      | DG         | 1.20   | -310 | 0.012     |
| B      | DG         | 1.10   | -315 | 0.008     |
| C      | DG         | 1.15   | -312 | 0.020     |
| D      | DGDpD3D4   | 0.95   | -305 | 0.065     |
| E      | DGDpD3D4   | 0.90   | -308 | 0.070     |
| F      | DGDpD3D4   | 0.98   | -302 | 0.055     |

redchi/aic/bic are INPUTS (computed upstream in fit.py, pulled from
RESULT_COLUMNS). selectors.py never recomputes them — it only ranks on them.
bic tracks aic's ordering here, so I show aic and note bic matches.

In code this table is one `group` in audit()'s
`for _, group in study_df.groupby("case_id")` loop, handed to `_spectrum_units`.

---

## READ-ITEM 1 — non-finite dropped first, SAME config set per selector

Confirmed at the top of `_spectrum_units`:
`valid = group[np.isfinite(group["id_ig"]) & np.isfinite(group["abs_error"])]`
runs ONCE per spectrum, before any selector loop. The surviving `valid` frame is
then reused for every selector and every stratum below — the three selectors
never see different config sets on the same spectrum. All six rows here are
finite, so all six survive for redchi, aic, and bic alike.
Status: CORRECT (uniform filter, applied before ranking, shared across selectors).

---

## READ-ITEM 2 — Spearman rho with average-rank ties

Confirmed in `score_configs`: `rho = float(spearmanr(sv, ae).correlation)`, inside
a `warnings.catch_warnings()` block, with the n<2 / constant-input guard returning
nan. scipy.stats.spearmanr uses average-rank tie handling by definition — not
argsort-as-rank, not rankdata ordinal/min/dense.

FULL stratum, redchi: sv=[1.20,1.10,1.15,0.95,0.90,0.98], ae=[.012,.008,.020,.065,.070,.055]
  redchi ranks A=6 B=4 C=5 D=2 E=1 F=3; abs_error ranks A=2 B=1 C=3 D=5 E=6 F=4
  Sum d^2 = 16+9+4+9+25+1 = 64; rho = 1 - 6*64/(6*35) = -0.829
  -> lower redchi points at the LESS accurate configs (the overfitting signature).

FULL stratum, aic: sv=[-310,-315,-312,-305,-308,-302], same ae
  aic ranks A=3 B=1 C=2 D=5 E=4 F=6; Sum d^2 = 10; rho = 1 - 60/210 = +0.714
  -> AIC orders configs roughly the way accuracy does.

Status: CORRECT (spearmanr, average-rank ties, guarded for degenerate inputs).

---

## READ-ITEM 3 — first-occurrence argmin, used consistently for BOTH regret and hit

Confirmed in `score_configs`: `sel_min = int(np.argmin(sv))` is computed ONCE and
used for both `top1_regret` (ae[sel_min] - oracle) and `top_quartile_hit`
(ae[sel_min] <= thr). np.argmin returns the FIRST occurrence on ties.

I RATIFY this convention: when two configs tie for lowest selector value, the
first config in the frame's order is "the selector's pick." This is deterministic
and defensible — ties in continuous redchi/AIC/BIC are measure-zero in practice —
and it is applied identically to regret and quartile-hit (no second, divergent
derivation of the pick). This is the one genuine convention choice in the module
and I accept it.
Status: CORRECT and RATIFIED.

---

## READ-ITEM 4 — regret >= 0 by construction

Confirmed in `score_configs`:
`oracle_min = float(np.min(ae)); top1_regret = float(ae[sel_min] - oracle_min)`.
Operands in the right order (selector's pick minus the global minimum abs_error
over the SAME surviving config set). Cannot go negative.

  FULL redchi: sel_min=E (redchi 0.90), oracle=B (0.008) -> regret = 0.070-0.008 = 0.062
  FULL aic:    sel_min=B (aic -315),  oracle=B (0.008) -> regret = 0.008-0.008 = 0.000

On the aic path the selector picks the genuinely best config, so regret is exactly
0 — matching the V4 rigged-correlated case at the code-path level, not just at the
test output.
Status: CORRECT (sign convention right; >= 0 holds on every value computed).

quartile-hit, same trace: thr = np.percentile(ae,25) = 0.014.
  FULL redchi: ae[E]=0.070 <= 0.014? No  -> hit = 0
  FULL aic:    ae[B]=0.008 <= 0.014? Yes -> hit = 1
Single threshold computed once, single `<=` inclusivity rule. Status: CORRECT.

So one spectrum, FULL stratum: redchi {rho -0.83, regret 0.062, hit 0} vs
aic/bic {rho +0.71, regret 0, hit 1}. Reduced chi^2 actively misleads; AIC picks
the best config. This is Q2 in miniature, and it is why all three metrics are
reported: rho catches the global anti-trend, regret prices the bad pick in ratio
units, hit reports "not even good enough."

---

## within_peak_set stratum — confirms the split the manual stratifies for

`_spectrum_units` does `valid.groupby("peak_set")` and scores each subframe
separately, appending one row per peak_set per selector (this is why the real
audit shows within_peak_set n_units = 90 for 30 spectra: 3 peak sets x 30).

  redchi within DG {A,B,C}: rho = +0.5; argmin(redchi)=B = most accurate -> regret 0, hit 1
  redchi within 5-band {D,E,F}: rho = -1.0; argmin(redchi)=E, oracle=F(0.055)
                                -> regret = 0.070-0.055 = 0.015, hit 0

redchi is fine within the simple DG set but perfectly anti-predictive within the
complex set — once inside an overfitting peak set, "lower redchi" just means "more
overfit." The FULL-stratum rho was mostly the peak-set decision; within_peak_set
unmasks where the selector genuinely helps vs hurts. Confirmed the code produces
exactly this two-row-per-spectrum structure.

Note: Spearman on 2 configs is always exactly +/-1, so within_peak_set is only
meaningful when each peak set holds enough configs. In the real grid each peak set
spans ~24+ configs (baseline x lineshape x bwf x intensity), so it is not
degenerate. (Logged as an interpretation caveat, not a code defect.)

---

## READ-ITEM 5 — bootstrap resampling unit is the SPECTRUM (not config, not row)

Confirmed in `_aggregate_group`. The bootstrap loop:
  `sampled = rng.choice(uniq, size=uniq.size, replace=True)`   <- resamples case_ids
  `sel = np.concatenate([idx_by_case[c] for c in sampled])`    <- pulls ALL rows of each
A clustered bootstrap: when a spectrum is drawn, every one of its sub-units (e.g.
each peak_set in within_peak_set) travels together. It is NOT resampling rows or
configs, NOT resampling within a spectrum. n_boot = 1000 (module constant N_BOOT).

Seed: `_group_seed` mixes the project SEED with the group key via zlib.crc32 and is
explicitly order-independent (depends only on the key, not group iteration order).
The rng is constructed once per cell and passed in, so no re-seeding inside the
loop. Project SEED imported from .synth (= 20260615).
Status: CORRECT (spectrum-level clustered bootstrap, 1000 draws, project SEED,
order-independent, no in-loop re-seed). This was the highest-risk line; read slowly.

---

## READ-ITEM 6 — pooling is MEDIAN of per-spectrum rho, not a mean of correlations

Confirmed in `_aggregate_group.stats`:
  rho    -> np.nanmedian
  regret -> np.nanmedian
  hit    -> np.nanmean (a hit RATE, which is correctly a mean of 0/1)
The point estimate and the bootstrap percentile CIs both run through this same
`stats` function, so point and interval use an identical statistic. No plain
arithmetic mean of raw rho values is presented anywhere as the estimate.
Status: CORRECT (median for rho/regret; mean only for the 0/1 hit rate, which is
the appropriate statistic for a rate).

---

## Other confirmations (not read-items, but checked while reading)

- coverage_under_misspecification (T6b): endpoints counted inclusively both ends
  (`true >= lo & true <= hi`), finite-row mask applied first. Definitional choice
  to POOL all grid configs per regime is the agent's settled scope call and is
  MINE to ratify in validation_plan.md (Part 15) — noted, decided there, not here.
- rigged_cases(): all three selector columns set identical and a single peak_set,
  so full and within_peak_set coincide and every selector reproduces the same exact
  answer — a clean construction for V4.

---

## VERDICT

Y — the rank/tie handling, the first-occurrence argmin (ratified), the regret sign
(>= 0 by construction), the quartile inclusivity (single threshold, single <=),
the spectrum-level clustered bootstrap (1000 draws, project SEED, order-independent),
and the median-not-mean pooling are all correct as read and match the manual's
P8 / Part VII spec. No BLOCKER found in the read. The pooled-T6b definition is a
ratification item I will settle in validation_plan.md, not a code defect.

Read independently cross-checked next by CX-4 (statistics audit).

— Avin Gupta, 2026-06-22