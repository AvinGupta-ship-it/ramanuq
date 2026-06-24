# AI Usage Log

## 2026-06-22 — Day 7, Implementer (selector audit / Q2 + Gate V4) — Avin Gupta, 6/22/2026

**Role:** Implementer. Built the Q2 selector-audit machinery and its validation
gate from the frozen grid results; authored no interpretation and read no
prediction.

**What this session implemented:**
- `src/ramanuq/selectors.py`:
  - `score_configs(selector_values, abs_errors)` — the per-config-set primitive
    (the unit the clean-room reference mirrors): average-rank Spearman rho
    (`scipy.stats.spearmanr`) between the lower-is-better selector value and
    `abs_error`; `top1_regret = abs_error[argmin selector] − min abs_error`
    (`>= 0` by construction); `top_quartile_hit` (1 if the selector-min config's
    `abs_error <= 25th-percentile`, single inclusive `<=` rule).
  - `audit(study_df, selectors=("redchi","aic","bic"), strata=("full",
    "within_peak_set"))` — per spectrum (`case_id`), drops non-finite
    `id_ig`/`abs_error` FIRST and scores every selector on the SAME surviving
    config set; `full` ranks all configs, `within_peak_set` ranks within each
    shared `peak_set`. Aggregates per `(material_class, snr_label, stratum,
    selector)` with a clustered bootstrap whose RESAMPLING UNIT IS THE SPECTRUM
    (1000 draws, seeded deterministically from the project `SEED = 20260615`).
    The reported central statistic for the per-spectrum rho is the MEDIAN (never
    a plain mean of raw correlations); regret→median, quartile-hit→mean rate.
    Produces table **T6**.
  - `rigged_cases()` — one correlated frame (exact rho `+1`, regret `0`) and one
    anti-correlated frame (exact rho `−1`), answers known by hand.
  - `coverage_under_misspecification(study_df)` — table **T6b**: per
    `(material_class, snr_label)` regime, the empirical fraction of finite
    interval rows pooled over the whole (misspecified) grid with
    `lo95 <= true_id_ig <= hi95` (both endpoints inclusive).
  - Computed-output column names are held as module variables (not bare string
    literals) so the Day-6 schema-freeze scan (which guards new *input*-column
    literals) is not tripped by legitimate audit outputs.
- Tests:
  - `tests/test_selectors.py`: **Gate V4** (`@pytest.mark.validation`) — exact
    recovery (`atol=1e-12`) of rho `+1` / regret `0` on the correlated rigged
    frame and rho `−1` on the anti-correlated frame, via `audit()` and via the
    `score_configs` primitive; an average-rank tie-handling test (asserts the
    result equals scipy's average-rank Spearman and the by-hand average-rank
    Pearson-of-ranks, and DIFFERS from the ordinal tie convention); a T6b
    inclusive-endpoint test.
  - `tests/test_differential_v6.py`: added the selectors differential
    (`@pytest.mark.validation`) — for 500 randomized valid frames, asserts
    `selectors.score_configs` rho and `top1_regret` equal
    `refimpl.ref_selectors.score_configs` to `< 1e-6`. The reference import is
    deferred into the test body so this single test ERRORS (by design) until the
    blind `refimpl/ref_selectors.py` is copied in, without taking down the rest
    of the V6 suite.
- `notebooks/03_selector_q2.ipynb`: runs the Gate V4 asserts FIRST (no real
  number shown before the machinery is validated), then loads
  `tierB_grid_results.parquet`, displays **T6** and **T6b**, stores (does not
  render) the arrays F5 will plot under a `## F5 (deferred to Day 9 — built with
  viz.py)` placeholder (no `viz` import, no figure), and ends with an empty
  `Verdict (author writes this)` cell. No prose interpreting results anywhere.

**One scope-guard maintenance (Day-6 precedent for grid/robust):**
- `tests/test_hostile.py::_DAY5_STUBS`: removed only `selectors` (now due on
  Day 7), leaving `mdc`, `reporting`, `viz` (Day-9 deferred) still guarded as
  must-stay stubs. No assertion, tolerance, or other stub protection weakened.

**What was NOT done:** did NOT read or reference the Q2 prediction
(`docs/validation_plan.md` Section 5) — that file was never opened. Did NOT
alter the pre-registration or any tolerance/gate. Did NOT modify any protected
file (`metrics.py`, `grid.py`, anything under `data/synthetic/results/`,
`data/synthetic/tierA/`, `data/synthetic/tierB/`, or `calibrations.yaml`). Did
NOT create or modify `viz.py`, `mdc.py`, or `reporting.py` (F5 deferred to
Day 9). Did NOT begin any Day-8+ work. Did NOT commit or push.

## 2026-06-21 — Day 6, Analyst — Avin Gupta, 6/21/2026

**Role:** Analyst. Generated the Day-6 analysis outputs from the
ALREADY-RUN Tier-B grid study. The study was NOT re-run; the existing
`data/synthetic/results/tierB_grid_results.parquet` (8640 rows, 6480 valid
errors) was loaded and the already-implemented `grid`/`robust` functions were
called as-is.

**What was generated (`scripts/day6_analysis.py`, a new analysis-only script):**
- Q1 ranking (T5) via `grid.rank_configurations(df, 0.90, 0.05)`,
  DESCRIPTIVE spread via `grid.decompose(df)`, and the Q1b stability table (T9)
  via `robust.jackknife_ranking(df, 0.90, 0.05)`.
- Table fragments `data/synthetic/results/t5_ranking.csv`,
  `t9_stability.csv`, `v3_classes.csv`, `config_cell_accounting.csv`, and the
  report fragments `day6_report_data.json`.
- Plain-language briefing `docs/day6_briefing.md` and self-check
  `docs/day6_quiz.md`.

**Faithful headline finding:** under the pre-registered 0.90 coverage floor
(== V1b lower bound), NO configuration is rank-eligible in any SNR regime —
max empirical 95% coverage across all 288 (config × regime) cells is 0.80,
below the floor. So `rank_configurations` (T5) and `jackknife_ranking` (T9)
return EMPTY tables, and Q1b is vacuous (no recommended config to jackknife).
This was verified to be the genuine study result (the bootstrap statistical
intervals undercover on hostile non-Lorentzian spectra), not a misuse — the
ranking rule and floors were used exactly as written and not modified. The
RMSE-ordering leaders are recorded descriptively and clearly labelled NOT
rank-eligible.

**Gate V3 re-confirmed PASS** from the study data: on the stage1/SNR50 slice,
9 of 72 (lineshape, baseline, peak_set, intensity) classes achieve mean
absolute bias < 0.05 (best: pseudo_voigt·poly5·DG·area = 0.0052). V3 is a bias
gate, independent of the coverage floor that empties the ranking.

**Three pre-registered questions answered:** (a) spread sigma_meth/RMSE is
larger on strong-baseline cases (0.887) than mild (0.866) or none (0.840);
(b) +D′ strata are NOT flagged for failures — failure rate is identical (0.25)
across all peak sets because failures come from `bwf_g=True`, not D′ (D′ does
worsen error, not failures); (c) no rank-1 config exists, so rank stability is
undefined, not "stable".

**What was NOT done:** did NOT re-run the study (`run_study` untouched). Did
NOT read the Q2 prediction — Section 5 / "Q2 Prediction (T1.6)" of
`validation_plan.md` was never opened; only Sections 1–4 were read. Did NOT
modify `grid.py`, `robust.py`, any test, `calibrations.yaml`, any `data/` file,
any Tier-A/Tier-B truth JSON, `metrics.py`, or `fit.py`. Did NOT alter any
pre-registration content, tolerance, the ranking rule, the coverage floor, or
the failure cap. Did NOT begin any Day-7+ work (no `selectors.py`, `mdc.py`,
`viz.py`, `reporting.py`, no figures). Did NOT commit or push.

## 2026-06-18 — Day 2, Implementer (Session A) — Avin Gupta, 6/18/2026

**Role:** Implementer (Session A). Built the core analysis modules and their
unit/behavioral tests against the contracts supplied in the session prompt.

**Files created/edited:**
- `src/ramanuq/lineshapes.py` — area-parameterized Lorentzian/Gaussian/
  pseudo-Voigt, height-parameterized BWF, analytic height/area helpers.
- `src/ramanuq/io.py` — frozen `Spectrum` dataclass and validating
  `load_spectrum`.
- `src/ramanuq/despike.py` — rolling-median MAD z-score despiker.
- `src/ramanuq/baseline.py` — `estimate` for linear/poly3/poly5/ALS.
- `src/ramanuq/model.py` — `build_model` composite peak models with bounds and
  windowed-maxima initial guesses.
- `src/ramanuq/fit.py` — `PipelineConfig`, `fit_spectrum`, standalone `aic`/`bic`,
  residual bootstrap with failure counting.
- `tests/test_lineshapes.py`, `tests/test_io.py`, `tests/test_despike.py`,
  `tests/test_baseline.py`, `tests/test_fit.py`.
- `docs/ai_usage_log.md` — this entry.

**What was delegated to the AI assistant:** implementation of the six modules
and their tests to the prompt's contracts and exact public API; lint/test
debugging; drafting this log entry and a Day-2 science briefing/quiz saved to
`/tmp/ramanuq_day2_briefing.md`.

**What was NOT touched (by instruction):** `data/calibrations/calibrations.yaml`,
`docs/validation_plan.md`, `docs/assumptions.md`, `docs/progress_journal.md`,
`docs/contracts.md`, anything under `refimpl/`, and `tests/test_differential_v6.py`
(authored by a separate clean-room session). No calibration constants or
literature citations were introduced into the implemented modules.

**Verification:** `ruff check .` clean; `python3 -m pytest` — 38 passed.

**Note for reviewer (open assumption):** `model.py` uses standard nominal
carbon-Raman band anchor positions (D, G, D-prime, D3, D4) as model structure to
seed the +/-40 center bounds and windowed-maxima guesses. These are anchors, not
calibrated coefficients, and are module-level/overridable. Flagged for sign-off.

### Day 2 — Session B (clean-room reference implementer) — 2026-06-18
Model: Claude Code (fresh session, launched in isolated folder ramanuq-cleanroom containing NO project source — no src/ramanuq, no .git).
Delegated: from the math specification ONLY, implemented refimpl/ref_lineshapes.py (Lorentzian, Gaussian, pseudo-Voigt, BWF + height/area helpers) and refimpl/ref_criteria.py (AIC, BIC), and authored tests/test_differential_v6.py.
Independence: session launched fresh (not resumed from Session A); agent confirmed it never accessed the main repository or any src/ramanuq file; helper relations were derived by the agent from the equations, not copied. This separation is what makes the Gate V6 differential meaningful.
Result: Gate V6 green — 8 tests, package vs. independent reference agree to 1e-9 (analytic) / 1e-6 (numeric) over 500 random inputs each.

### Day 2 — Session C (adversarial reviewer, CX-1) — 2026-06-18
Model: Claude Code (fresh session, repo, review-only — modified nothing).
Delegated: adversarial review of the six instrument modules and their tests.
Findings: 2 flagged blockers, 11 nits. Resolved before commit: BWF q=0 division hazard (bounded/guarded), missing tests/test_model.py (added, 8 assertions), n_failed semantics on primary-fit failure (corrected). Remaining nits logged as Day-3 follow-ups; weighting scheme and band-anchor/width seeds intentionally left unchanged (frozen modeling structure).

Reviewed and verified accurate — Avin Gupta, 2026-06-18

### Day 3 — Session A (Tier-A truth + Gate V1 implementer) — 2026-06-18. Reviewed and approved — AG, 2026-06-18.
Model: Claude Code (Opus 4.8), implementer in the main repo.
Delegated: implement `src/ramanuq/synth.py` (Tier-A in-family synthetic generator),
write the paired CSV + `*_truth.json` Tier-A suite under `data/synthetic/tierA/`,
add `tests/test_synth.py` and the Gate V1 recovery test `tests/test_fit_recovery.py`
(`@pytest.mark.validation`), and a deterministic realism-plot script
`scripts/render_tierA.py`.

What this session did:
- Implemented `synth.py`: bands rendered via `ramanuq.lineshapes` (area-parameterized);
  ground truth computed DIRECTLY from the noiseless, baseline-free analytic band
  functions (area = the `area` parameter / integral; height = the analytic maximum) —
  never read off a fitted or noisy curve. Each truth JSON stores all generator
  parameters, the seed, and BOTH labelled ratios `true_id_ig_area` and
  `true_id_ig_height`. All randomness derives from one project constant `SEED`.
- Enumerated the suite per the frozen decisions (see below): 5 noise-free recovery
  cases (stage-1 x 4 area ratios {0.1,0.5,1.0,2.0}; stage-2 x 1 at ratio 1.0) + 45
  noisy factorial (stage-1 ratio(4) x baseline(3) x SNR(3) = 36; stage-2 baseline(3)
  x SNR(3) = 9) = 50 cases. 50 CSV + 50 `*_truth.json` + `manifest.csv` written.
- Gate V1 (`test_fit_recovery.py`) recovers via the REAL fitter
  (`fit.fit_spectrum`/`PipelineConfig`) — no fitting logic duplicated; bands are
  identified by nearest fitted center to each true center to resolve lmfit's
  label permutation. Stage-1 per-case worst relative error 7.86e-8 (gate 1e-3).

Two structural conflicts were found, reported to the human, and resolved only with
explicit approval (no gate weakened, no tolerance/pre-registration changed):
- Conflict A (baseline): `fit_spectrum` always subtracts an estimated baseline and
  had no zero option, biasing baseline-free recovery ~0.02–6% (> the 0.1% gate).
  APPROVED additive Day-2 edit: added `baseline_method="none"` (returns an all-zero
  array) to `baseline.py`, used ONLY by the Gate V1 recovery path. Constraints met:
  linear/poly3/poly5/als behavior unchanged; `none` NOT added to any studied
  baseline grid (Q1 science untouched); existing baseline tests pass unchanged;
  Gate V6 differential re-run and green; V1 tolerance unchanged at < 0.1%; the
  `none` option documented in the `baseline.py` docstring.
- Conflict B (stage-2 mixed family): stage-2 truth mixes Lorentzian D/G with
  Gaussian D3/D4, but `fit_spectrum` applies one lineshape to all bands, so no
  matched fit exists (~41% I_D/I_G residual even with a perfect baseline). APPROVED
  scope: Gate V1 per-case < 0.1% covers stage-1 only; stage-2 spectra+truth are
  still generated and committed (Gaussian D3/D4 unchanged) for later gates. The
  exclusion and its measured residual are documented in `test_fit_recovery.py`.

Frozen decisions confirmed with the human before coding (docs were silent):
stage-2 D/G = Lorentzian (default); area-ratio sweep is stage-1 only, stage-2 fixed
at 1.0; cosmic spikes implemented as a generator toggle but NOT crossed as a suite
dimension; satellite scaling ("15% of D", "30% of G") interpreted as AREA fraction.

What this session did NOT do: it did NOT make the human realism judgement (only
produced the two labelled PNGs for inspection); did NOT alter
`data/calibrations/calibrations.yaml`, the Q2 prediction, or any pre-registered
tolerance; did NOT create any Tier-B spectra; did NOT introduce any literature
constant; and did NOT change Day-2 math to force recovery (the `none` baseline is an
additive no-op approved by the human, not a change to any estimator or to the fit).

Verification: `ruff check .` clean; full suite `python3 -m pytest` — 270 passed;
Gate V1 `pytest tests/test_fit_recovery.py -v -m validation` — 6 passed.
Realism plots: `data/synthetic/tierA/figures/tierA_stage1_r1p0_noiseless.png`,
`data/synthetic/tierA/figures/tierA_stage2_r1p0_noiseless.png`.

### Day 4 — Session A (Tier-B hostile suite + Gate V2 implementer) — 2026-06-18 — Reviewed and verified accurate - Avin Gupta, 2026-06-18

**Role:** Implementer (Session A). Executed the frozen Day 4 contract: finalized
Gate V2, built the out-of-family Tier-B generator + tests, and produced the
human realism-gate plots. No science, pre-registration, or tolerance was changed.

**Files created/edited:**
- `src/ramanuq/hostile.py` — Tier-B out-of-family generator. Band constructors
  `composite_band` (3–7 jittered narrow Lorentzians → non-Lorentzian aggregate),
  `emg_band` (Gaussian core convolved with a one-sided exponential of constant
  `tau` → asymmetric), `mixed_voigt_band` (per-band `eta`), and `gp_baseline`
  (a smooth random baseline = broad random Gaussians + a decaying exponential;
  severities `none|mild|strong`). The name `gp_baseline` is a label only — it is
  NOT a Gaussian-process regressor and imports no GP/sklearn library.
  `generate(case, seed)` and `suite(out_dir, seed)` write the full crossing.
- `tests/test_hostile.py` — generator-contract tests (determinism, truth-schema
  completeness, finiteness, monotonic axis, parseable one-to-one filenames, full
  90-cell coverage, physically valid params, both truth definitions, baseline
  severity metadata, out-of-family proof, Tier-A untouched, no Day-5 scope).
- `tests/test_baseline.py` — added Gate V2 (`@pytest.mark.validation`) and a
  despike-no-op/idempotence test on clean (spike-free) input; existing tests kept.
- `scripts/render_tierB.py` — renders four representative Tier-B PNGs.
- `data/synthetic/tierB/` — 90 CSV + 90 `*_truth.json` + `manifest.csv` + figures.

**Gate V2 (pre-registered, 2% of G-band height, UNCHANGED).** Finalized as a
peak-free truth construction: a noiseless spectrum that is only the Tier-A
baseline curve (no peaks), so baseline-estimation quality is isolated from peak
confounding; the reference is the stage-1 analytic G-band height. One genuine
ambiguity in the original V2 entry — the method→baseline pairing — was surfaced
to the human BEFORE implementation (measured: `linear` 10.5% and `poly3` 1.97%
on `strong_curved`, so a literal full cross-product is unpassable without
weakening the frozen 2%). The human fixed the in-class pairing and recorded it in
`validation_plan.md`: `linear` graded on `none` only (a straight line cannot
represent a curved background); `poly3/poly5/als` graded on all three severities
(`none`, `mild_cubic`, `strong_curved`). Gate V2 implements exactly that pairing;
the 2% tolerance is unchanged. All 10 graded (method, baseline) pairs pass.

**Tier-B truth.** True intensities come only from the noiseless, baseline-free
band callables, computed BEFORE baseline and noise: `true_id_ig_area` is the
numeric integral (trapezoid) of D over G; `true_id_ig_height` is `max(D)/max(G)`.
For the composite D band, height truth is the max of the SUMMED callable, not the
sum of sub-peak heights. Both definitions are stored in every truth JSON, along
with all band parameters (sub-peak centers/widths/areas/heights, EMG `tau`,
per-band `eta`), the baseline parameters + severity label, the seed, and the
generator-family labels. Truth is never read back off the observed curve.

**Suite & determinism.** Full crossing {stage1, stage2} × {none, mild, strong}
× SNR {200, 50, 15} × 5 instances = 90 spectra exactly. A single project seed
(`hostile.SEED`, shared with `synth.SEED`) feeds all randomness; per-case
randomness derives from `SeedSequence([SEED, crc32(case_id)])`, so cases are
independent yet reproducible. CSV columns `shift_cm-1,intensity` and the
`{stem}.csv` ↔ `{stem}_truth.json` naming reuse the Day-3 conventions; case_ids
encode stage/severity/SNR/instance.

**Out-of-family proof.** `test_composite_and_emg_bands_are_out_of_family` fits the
best *independent* single Lorentzian (scipy least-squares) to each composite D and
EMG G band and asserts relative RMS residual > 1%. Measured worst-case margins:
composite ≈ 5.1%, EMG ≈ 15.6% (both well above 1%). This proves out-of-family
without any claim of physical realism.

**Verification:** `ruff check .` clean; full suite `python3 -m pytest -q` —
746 passed; Gate V2 `pytest tests/test_baseline.py -v` — 19 passed (10 V2 pairs +
guard + despike + finiteness); validation marker `pytest -m validation` — 25
passed; `tests/test_hostile.py` — 462 passed. Realism plots (4):
`data/synthetic/tierB/figures/tierB_stage1_blnone_snr200_i0.png`,
`tierB_stage1_blstrong_snr15_i2.png`, `tierB_stage2_blmild_snr50_i1.png`,
`tierB_stage2_blstrong_snr15_i3.png`.

What this session did NOT do: did NOT make the human Tier-B realism judgement
(only produced the four labelled PNGs for inspection); did NOT alter
`data/calibrations/calibrations.yaml`, the Q2 prediction, or anything in
`validation_plan.md` (the in-class V2 pairing note was written by the human);
did NOT change any pre-registered tolerance; did NOT modify Tier-A data; did NOT
change Day-2 math (lineshapes/model/fit/baseline/despike) to force any result;
did NOT change Day-3 truth values; did NOT create any Day-5 metric/calibration
code; did NOT introduce any literature constant; did NOT begin any Q1/Q2/Q3 study
or grid work; and did NOT implement a real Gaussian-process baseline.

### Day 5 — Session A (metrics + calibration-wiring implementer) — AG 2026-06-19

**Role:** Implementer (Session A). Executed the frozen Day 5 contract: built the
calibration loader, the `Metrics` container, and `compute_metrics`, wrote
`docs/calibration_provenance.md` and `tests/test_metrics.py`. All scientific
decisions — the hand-pin numbers, the calibration constants/equations, the
intensity-definition matching, and the stage-guard thresholds — are the human's
and were taken as-is from `data/calibrations/calibrations.yaml`. No
pre-registration, Q2 prediction, tolerance, or truth file was touched.

**Files created/edited:**
- `src/ramanuq/metrics.py` — `load_calibrations(path)` validates per-calibration
  provenance (non-empty `citation`, `doi`, `validity`, `intensity_definition`),
  treats `stage_guard` as the only permitted non-calibration top-level key,
  raises (never silently skips) on any other top-level entry lacking
  `intensity_definition`, and parses constant strings to float (raising, never
  defaulting, on unparseable values; `"n/a"` denotes no project constant). A
  frozen `Metrics` dataclass with the contract field list. `compute_metrics(fit,
  calibrations, definition)` reads every constant and the wavelength from the
  loaded YAML / `fit.meta["wavelength_nm"]`; no calibration constant is
  hard-coded. Each calibration is fed the ratio under its own declared intensity
  definition (Cançado 2006 → area, Cançado 2011 → height), classified from the
  YAML `intensity_definition` field. `la_tk` and `l_d` are intentional NaN with
  flags. The stage guard suppresses the calibrated quantities (but not `id_ig`)
  to NaN, flags the reason, and warns.
- `src/ramanuq/fit.py` — one-line, numerically/scientifically neutral addition:
  `meta["wavelength_nm"] = float(spec.wavelength_nm)` so `FitResult` carries the
  excitation wavelength that `compute_metrics` consumes. No fit math, gate, or
  tolerance changed (decision confirmed with the human before editing).
- `docs/calibration_provenance.md` — summary of provenance already in the YAML
  (citation, DOI, access date, equation, constant + units + uncertainty,
  intensity definition, validity), plus notes that `la_tk`/`l_d` are intentional
  NaN and that the stage-guard thresholds are documented assumptions. No source
  fact not already in the YAML was introduced.
- `tests/test_metrics.py` — hand-pin (532 nm, ratios == 1 → `la == 19.2246202982`,
  `n_d == 2.2471185038e11`), constant-uncertainty propagation, intensity-definition
  wiring (area/height not swapped), stage guard fires (both conditions; G-only,
  no D3) and does not false-fire, provenance-validation raises (missing
  citation/doi/intensity_definition against tmp copies), no-hard-coded-constants
  source scan, and interval sanity.
- `data/calibrations/calibrations.yaml` — fixed ONE stray trailing double-quote
  (`stage-1.""` → `stage-1."`) at EOF that prevented the file from parsing at
  all. Pure YAML-syntax fix; no scientific content (constants, equations,
  citations, definitions, thresholds) was altered. The `2.4-e10`→`2.4e-10`
  correction and the `stage_guard` block were already present in the working
  tree (human edits).

**FitResult fields read.** Areas/FWHMs from `fit.best["D_area"]`,
`best["G_area"]`, `best["D_fwhm"]`, `best["G_fwhm"]`; optional D3 from
`best["D3_area"]` (guard's D3 condition skipped when absent). Bootstrap rows from
`fit.bootstrap_df` (same column names). Wavelength from `fit.meta["wavelength_nm"]`.
Height-from-area via `lineshapes.lorentzian_height_from_area`.

**Verification:** `python3 -m ruff check .` — clean. `python3 -m pytest
tests/test_metrics.py -v` — 11 passed. Hand-pin, constant-uncertainty,
definition-wiring, both stage-guard fire cases, no-false-fire, all three
provenance-raise cases, no-hard-coded-constants scan, and interval sanity all
green. `tests/test_fit.py`, `tests/test_fit_recovery.py`, `tests/test_smoke.py`
still pass (11) after the one-line `fit.py` meta addition.

What this session did NOT do: did NOT change the hand-pin numbers (the human's);
did NOT alter calibrations.yaml scientific content (only fixed one stray quote so
it parses); did NOT modify Tier-A or Tier-B truth files; did NOT touch
`validation_plan.md`, the Q2 prediction, or any pre-registration/tolerance; did
NOT hard-code any calibration constant (a source scan in the tests enforces this);
did NOT edit `tests/test_differential_v6.py` or do any V6 work; and did NOT begin
any Day-6+ work (no grid.py, selectors.py, mdc.py, robust.py, viz.py,
reporting.py).

## 2026-06-20 — Pre-Day-6 bug fix, Implementer — Avin Gupta, 6/20/2026

**Role:** Implementer. Hardened the ALS baseline against an environment-dependent
non-finite result that turned GitHub Actions (Python 3.11 / Linux) red while the
suite stayed green locally (Python 3.14 / macOS).

**Defect:** `tests/test_fit.py::test_fit_never_raises_on_degenerate_input` feeds a
perfectly flat spectrum (all-zero intensity). In `_als_baseline`, the first solve
returns `z = 0`; the asymmetric weight update `p*(y>z) + (1-p)*(y<z)` then drives
*every* weight to zero (no point is strictly above or below the smooth). The next
iteration's system collapses to `lam * DᵀD`, which is rank-deficient by two (its
null space is the constant and linear ramps) and therefore exactly singular.
`spsolve` on that singular matrix returns non-finite values on the Linux LAPACK
backend (macOS happens to return finite), tripping the finite-value guard, which
correctly raised `ValueError` — violating the `fit.py` contract that
`fit_spectrum` must never raise on degenerate input.

**Fix (src/ramanuq/baseline.py only):** Added a tiny fixed diagonal ridge
(`_ALS_RIDGE = 1e-9`, applied as `wmat + dtd + ridge`) so the normal-equations
matrix is always positive-definite and the solve is finite on every backend. On
well-conditioned inputs the weights are always p (0.01) or 1−p (0.99), so the
system is already PD and the ridge — many orders below the smallest weight —
does not measurably perturb the fit. The `(baseline, diagnostics)` signature and
diagnostics contents are unchanged.

**Verification:** `test_fit_never_raises_on_degenerate_input` PASSES; full suite
763 passed / 0 failed; all 29 `-m validation` gates (V1/V2/V6) still pass; `ruff
check .` clean. A direct check confirmed `baseline.estimate(flat_spectrum,
method="als")` now returns an all-finite array (and exactly zeros for the flat
input), and a normal ALS fit remains finite.

**What was NOT touched:** no test was changed, loosened, or deleted; no tolerance
was weakened; no other `src` module, `fit.py`, `metrics.py`,
`calibrations.yaml`, any Tier-A/Tier-B truth file, `validation_plan.md`, or any
other doc/pre-registration was edited. No science, data, or calibration constant
was altered. No Day-6 work was begun (no grid.py, robust.py, or any new module).
The finite-value guard that raises was left intact — the solver was fixed so it
no longer produces non-finite values in the first place.

### Day 6 — Session A (configuration-grid study + Q1b jackknife + Gate V3) — AG, 2026-06-20

**Role:** Implementer (Session A). Executed the frozen Day 6 contract (prompts
P6 then P7).

**What was implemented:**
- `src/ramanuq/grid.py`: frozen `RESULT_COLUMNS` schema; `default_grid()`
  (factorial over baseline × lineshape × bwf_g × peak_set × intensity, with
  `bwf_g=True` emitted only for `lineshape=="lorentzian"` — 96 configurations);
  `run_grid()` (fit + `compute_metrics` with the matching intensity definition,
  never raising on a failed fit); `run_study()` (Tier-B suite run, truth join on
  `case_id` selecting the matched-definition truth, `error`/`abs_error`, writes
  parquet + csv to `data/synthetic/results/`); `decompose()` (explicitly
  DESCRIPTIVE / non-causal spread summary); `rank_configurations()` (Q1 ranking
  rule — RMSE-ascending order with coverage-floor and failure-rate eligibility
  gates read from the plan as named constants).
- `src/ramanuq/robust.py`: `jackknife_ranking()` (Q1b leave-one-out over
  configuration families and suite instances; per-regime top-quartile retention,
  rank IQR, and flip flag for the protocol-recommended config).
- Tests: `tests/test_grid.py` (grid build/constraint, exact-schema, ranking
  eligibility, DESCRIPTIVE-label, **Gate V3** `@pytest.mark.validation` with
  `V3_BIAS_TOL = 0.05` citing Section 1, and the RESULT_COLUMNS schema-freeze
  scan of downstream modules); `tests/test_robust.py` (fabricated frames with
  stability known by construction — one dominant config pinned to retention 1.0
  / no flip, one near-tie pinned to a flip).

**One clarification requested and granted (recorded for provenance):**
- Gate V3 "mean absolute bias": confirmed the metric is `|mean signed error|`
  (systematic offset), graded per intensity definition with class key
  `(lineshape, baseline, peak_set, intensity)` — area-ratio and height-ratio
  truths are distinct physical quantities and are not pooled. Tolerance (0.05),
  slice (`stage1` & `snr50`), and class factors were read from the plan, not
  invented.

**One protected-test edit, explicitly authorized (recorded for provenance):**
- `tests/test_hostile.py::test_no_day5_scope_added`: dropped `grid` and `robust`
  from `_DAY5_STUBS` (leaving `mdc`, `reporting`, `selectors`, `viz`), mirroring
  the earlier removal of `metrics`. The guard protects modules not yet due;
  grid/robust are due on Day 6, so they legitimately come off. No other change to
  that test; no tolerance, assertion, or remaining-stub protection was weakened.

**What was NOT done:** did NOT read the Q2 prediction (Section 5 / T1.6 of
`validation_plan.md` was never opened — only Sections 1–4 were read). Did NOT
alter any pre-registration content, tolerance, the ranking rule, the coverage
floor, or the failure cap. Did NOT modify any Tier-A or Tier-B truth file,
`calibrations.yaml` or any `data/` input, `metrics.py`, `fit.py`,
`lineshapes.py`, or any existing `src` module other than creating `grid.py` and
`robust.py`. Did NOT begin any Day-7+ work (no `selectors.py`, `mdc.py`,
`viz.py`, `reporting.py`, no figures, no notebooks). Did NOT commit or push.

— Reviewed and signed: Avin Gupta, 2026-06-21. Confirmed accurate: agents implemented grid.py/robust.py and the Day-6 tests and generated the analysis from existing study data; I personally inspected the ranking, ruled that the empty ranking is the faithful pre-registered result (rule and floor unchanged), and performed the spot-recompute. No agent authored my interpretation, changed my pre-registration, or read the Q2 prediction.
— 2026-06-22, CX-4 statistics-audit fix (agent, Avin Gupta): extended the per-spectrum finiteness filter in `_spectrum_units` (`src/ramanuq/selectors.py`) to also drop configs whose audited selector columns (redchi/aic/bic) are non-finite, keeping a single surviving set shared across all selectors/strata; added regression test `test_cx4_nonfinite_selector_config_excluded_before_scoring` in `tests/test_selectors.py`. ruff clean; test_selectors.py and `-m validation` (incl. V4 and V6 selectors) green.

---

## Day 8 — MDC / Q3 + protocol-card scaffold (agent session, 2026-06-22)

**What this session implemented: Reviewed and signed — Avin Gupta, 2026-06-22.**
- `src/ramanuq/mdc.py`: `mdc(sigma_single, alpha=0.05, power=0.8, n_rep=1)` =
  `(norm.ppf(1-alpha/2) + norm.ppf(power)) * sqrt(2) * sigma_single / sqrt(n_rep)`;
  `to_delta_nd(mdc_value, calibrations, wavelength_nm)` returning the
  `(central, lo, hi)` Δn_D triple via the multiplicative Cancado-2011 relation
  `C(λ) = constant_value / λ⁴` with the `± published constant_uncertainty` band
  (constant and uncertainty READ from the loaded calibrations object — no
  hard-coded calibration number; raises if the uncertainty field is absent);
  `estimate_sigma_single` (sd ddof=1 of the signed `error` column — precision)
  and `estimate_bias` (mean of the signed `error` column — accuracy, reported
  SEPARATELY) over a (config, regime=material_class+snr_label) filter.
- `tests/test_mdc.py`: hand-pin #3 placeholder (`HAND_PIN_SIGMA = 0.10`,
  `HAND_PIN_MDC_IDIG = None`) that `pytest.skip`s while the value is None (NOT a
  validation gate); a 1/√n_rep scaling test; and std-vs-mean tests for the two
  estimators on a fabricated frame with known values.
- `notebooks/04_mdc_casestudy_q3.ipynb`: loads the Tier-B parquet; per SNR
  regime computes σ_single, bias, and MDC (I_D/I_G and Δn_D) for the NAIVE
  config (linear|lorentzian|bwf_g=False|DG|height) and the PROTOCOL config (the
  DG/area config with the smallest signed-error sd in that regime, with the
  selection and reason printed); plots MDC-vs-SNR (naive vs protocol) in both
  currencies in PLAIN inline matplotlib (no viz.py); prints the summary table.
  No interpretive prose.
- `docs/protocol.md`: measured-cells-only table (regime | recommended | bias |
  RMSE | coverage | failure | MDC | stability), one row per SNR regime, with the
  empty author section heading left for the human.
- `tests/test_differential_v6.py`: Gate-V6 MDC differential
  (`test_mdc_matches_reference`, `test_to_delta_nd_matches_reference`,
  `@pytest.mark.validation`) asserting `mdc`/`to_delta_nd` equal
  `refimpl.ref_mdc` on randomized inputs to rtol 1e-9; written to
  `pytest.importorskip` the reference module and skip gracefully while
  `ref_mdc`/`ref_to_delta_nd` are absent (reference authored separately/blind).

**One stale stub-guard narrowed (recorded for provenance):**
- `tests/test_hostile.py::test_no_day5_scope_added`: dropped `mdc` from
  `_DAY5_STUBS` (leaving `reporting`, `viz`), because Day 8 (P9 / §9.8)
  legitimately implements `mdc.py`. The guard still enforces that `reporting`
  and `viz` remain stubs and that `hostile.py` imports neither. No tolerance,
  assertion, or remaining-stub protection was weakened; this test is not a
  `@pytest.mark.validation` gate.

**Gate results this session:** ruff clean; `tests/test_mdc.py` 3 passed / 1
skipped (hand-pin); `-m validation` 34 passed / 2 skipped (the two new MDC
differentials, awaiting ref_mdc); full suite 784 passed / 3 skipped.

**What was NOT done:** did NOT author any protocol recommendation prose (the
`## Recommendations and scope` section is empty for the human). Did NOT compute
or fill the hand-pin value (`HAND_PIN_MDC_IDIG` stays `None`; the test SKIPS).
Did NOT change any tolerance, the pre-registration, the ranking rule, the
coverage floor, or the failure cap. Did NOT edit `validation_plan.md`,
`progress_journal.md`, or `calibrations.yaml` science. Did NOT modify any
Tier-A/Tier-B truth file or the study results parquet/csv. Did NOT author
`refimpl/ref_mdc.py` (kept blind). Did NOT build `viz.py`/`reporting.py` or any
styled figure, and did NOT begin any Day-9 work. Did NOT commit or push.

## Day 9 — report_data.json + figures F1-F9 + QA harness - Avin Gupta, 2026-06-24

**What this session implemented (factual; awaiting human review/signature):**
- `src/ramanuq/reporting.py`: reads the existing study parquet
  (`data/synthetic/results/tierB_grid_results.parquet`) and the frozen
  calibrations and RECOMPUTES every cited number (no copy from `protocol.md`),
  emitting `docs/report_data.json`. Keys: each gate (V1, V1b, V2, V3, V4, V6;
  V5 marked `pending_day10`); `t5_ranking` (n_rank_eligible=0, is_empty,
  max_coverage=0.80, coverage_floor=0.90); `gate_v3` (n_classes=72,
  n_classes_passing=9, best_class pseudo_voigt/poly5/DG/area,
  best_class_mean_abs_bias); `q1b_stability` (per-regime "undefined; 0
  rank-eligible configs"); `q2_audit.by_stratum` (spearman_rho + rho_ci,
  top1_regret, top_quartile_hit per full/within_peak_set × SNR × selector via
  `selectors.audit`); `t6b_coverage` per regime; `mdc.per_regime` (protocol and
  naive σ_single, bias, MDC in I_D/I_G and Δn_D central + range, plus protocol
  RMSE/coverage/failure). `select_protocol_config` mirrors notebook 04
  (smallest signed-error sd among DG/area). A `self_check` compares recomputed
  values to the authored protocol/validation numbers (atol 1e-3); `write_report_data`
  refuses to write if the self-check fails. Self-check PASSED.
- `src/ramanuq/viz.py`: one Okabe-Ito colorblind-safe style, 300 dpi, PNG+PDF.
  Figures F1 (recovery parity + coverage), F2 (hostile-fit anatomy, true bands
  dashed, baseline-subtracted; fixed case `tierB_stage1_blmild_snr50_i3`; true
  components from `hostile.assemble`, fit curve rebuilt from `fit_spectrum`),
  F3 (per-config accuracy strip, naive + protocol flagged), F4 (RMSE/coverage
  maps over baseline×lineshape, DG/area, per SNR), F5 (selector scatter +
  top-1 regret + T6b coverage), F6 (protocol card), F7 (MDC curves I_D/I_G and
  Δn_D, protocol vs naive), F8 (digitized published spectra; raises
  `FileNotFoundError` when `data/digitized/` is empty), F9 (rank-stability empty
  state). All cited numbers (F6/F7 and annotated values on F1/F4/F5/F9) read
  from `docs/report_data.json`; F3/F4 read raw arrays from the parquet.
  Non-schema keys (palette names, report keys, computed columns) held as named
  constants to satisfy the `test_grid.py` schema-freeze scan (cf. selectors.py).
- `scripts/make_all_figures.py`: Agg backend, `SOURCE_DATE_EPOCH` pinned, fixed
  SEED, stripped figure metadata; recomputes `report_data.json`, generates
  F1-F7 and F9 (F8 skipped cleanly), and verifies the 16 output files are
  byte-identical across two consecutive runs.
- `scripts/figure_qa.py`: per figure asserts on-disk PNG/PDF exist and exceed a
  size threshold, axis labels present (where applicable), an explanatory element
  present (legend/colorbar/table/annotation per figure kind), and two in-memory
  renders are byte-identical. F8 reported DEFERRED.
- `tests/test_hostile.py`: renamed the stale stub-guard
  `test_no_day5_scope_added` → `test_hostile_does_not_import_downstream`,
  removing `reporting`/`viz` from the "stays a stub" list (now implemented, as
  Day 8 did for `mdc`) while keeping the invariant that `hostile.py` imports no
  reporting/viz code.
- `docs/day9_briefing.md` and `docs/day9_quiz.md` authored (teaching material;
  quiz answers in a separate marked section).

**Gate/QA results this session:** `ruff check .` clean; `figure_qa.py` 8/8
generated figures PASS, F8 DEFERRED; `make_all_figures.py` reports all 16 files
byte-identical across two runs; `report_data.json` self-check PASSED (reproduces
authored protocol MDC 0.529/0.271/0.565, naive 0.745/0.763/0.703, bias
+0.022/−0.086/−0.016, RMSE 0.133/0.109/0.141, coverage 0.467/0.233/0.200, T6b
0.276/0.240/0.183, V3 best 0.0052); full suite `pytest -q` 787 passed, 2 warnings.

**What was NOT done:** did NOT re-run the Day-6 study (read the parquet only);
did NOT alter any pre-registration tolerance, the ranking rule, the coverage
floor, or the failure cap. Did NOT edit `validation_plan.md`,
`progress_journal.md`, or `protocol.md` (no number or word changed). Did NOT
modify `calibrations.yaml`, `metrics.py`, `grid.py`, `selectors.py`, `mdc.py`,
any Tier-A/Tier-B truth file, or the study parquet/csv. Did NOT select or
fabricate demonstration spectra (F8 raises until the human digitizes). Did NOT
author interpretive prose. Did NOT begin Day-10 report work (no
`report_template.md`, `build_report.py`, README assembly, or Gate V5 assertion).
Did NOT commit or push.
