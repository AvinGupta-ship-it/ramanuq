# Contracts

Transcribed from the code as of this commit. The single source of truth remains
the modules themselves; this file restates only what they already specify
(module docstrings, `__all__` exports, `RESULT_COLUMNS`, and the pre-registered
constants named in code). It invents nothing.

## Frozen result schema: `RESULT_COLUMNS` (src/ramanuq/grid.py)

`grid.RESULT_COLUMNS` is the single source of truth for the study result schema;
any downstream module references only names in this tuple for input columns. The
columns, in their frozen order, grouped by the in-code section comments:

- **spectrum / truth join keys:** `case_id`, `stage_label`, `snr_label`,
  `severity`, `instance`, `material_class`
- **configuration factors (the 5 DOF):** `baseline`, `lineshape`, `bwf_g`,
  `peak_set`, `intensity`
- **fitted metric + interval:** `id_ig`, `lo95`, `hi95`, `sigma_stat`,
  `n_failed`, `redchi`, `aic`, `bic`
- **calibrated quantities (NaN where stage-guarded / undefined):** `la`, `n_d`
- **truth + error (filled by the truth join in `run_study`):** `true_id_ig`,
  `error`, `abs_error`

## Pre-registered constants (src/ramanuq/grid.py)

- `COVERAGE_FLOOR = 0.90` — rank-eligibility coverage floor
  (validation_plan.md Section 3; == V1b lower bound 0.90 of the pre-registered
  coverage band 0.90-0.98).
- `MAX_FAILURE_RATE = 0.05` — rank-eligibility failure-rate cap
  (validation_plan.md Section 3).

## Operational truth keys (src/ramanuq/synth.py, src/ramanuq/hostile.py)

Both pre-registered truth definitions are stored per spectrum under labelled keys:

- `true_id_ig_area` — Tier A: the analytic band-area ratio `A_D / A_G`; Tier B:
  the ratio of the numeric integrals of the (noiseless, baseline-free) D and G
  band callables over the spectrum grid.
- `true_id_ig_height` — Tier A: the analytic band-height (line-shape maximum)
  ratio; Tier B: the ratio of the maxima of the D and G band callables.

Truth is computed before baseline and noise are added and is never read back off
the observed curve.

## Module public surface

### lineshapes — Analytic spectral line-shape functions (Gaussian, Lorentzian, Voigt, BWF).
No explicit `__all__`; public functions: `lorentzian`,
`lorentzian_height_from_area`, `lorentzian_area_from_height`, `gaussian`,
`gaussian_height_from_area`, `gaussian_area_from_height`, `pseudo_voigt`,
`pseudo_voigt_height_from_area`, `pseudo_voigt_area_from_height`, `bwf`.

### baseline — Baseline (background) estimation for spectra.
No explicit `__all__`; public function: `estimate`.

### despike — Detection and removal of cosmic-ray spikes from spectra.
No explicit `__all__`; public function: `despike`.

### io — Reading and validating Raman spectra and associated metadata.
No explicit `__all__`; public surface: `Spectrum`, `load_spectrum`.

### model — Composite spectral models assembled from line shapes.
No explicit `__all__`; public surface: `BandSpec`, `PEAK_SETS`, `SpectralModel`,
`build_model`.

### fit — Fitting pipeline: despike -> baseline subtract -> bounded WLS -> bootstrap.
`__all__`: `aic`, `bic`, `PipelineConfig`, `FitResult`, `fit_spectrum`,
`config_fields`.

### metrics — Calibration-derived Raman metrics (I_D/I_G, L_a, n_D) with provenance wiring.
`__all__`: `Metrics`, `load_calibrations`, `compute_metrics`.

### synth — Generation of synthetic Raman spectra for testing and validation (Tier A).
`__all__`: `SEED`, `Peak`, `Case`, `generate`, `enumerate_cases`,
`recovery_cases`, `suite`, `case_id`.

### hostile — Construction of adversarial ("hostile") spectra that stress the pipeline.
`__all__`: `SEED`, `SEVERITIES`, `SNR_LEVELS`, `N_INSTANCES`, `Case`, `case_id`,
`composite_band`, `emg_band`, `mixed_voigt_band`, `gp_baseline`, `assemble`,
`generate`, `enumerate_cases`, `suite`.

### grid — Configuration-grid study over the hostile (Tier-B) suite.
`__all__`: `RESULT_COLUMNS`, `COVERAGE_FLOOR`, `MAX_FAILURE_RATE`, `BASELINES`,
`LINESHAPES`, `PEAK_SETS`, `INTENSITIES`, `default_grid`, `run_grid`,
`run_study`, `decompose`, `rank_configurations`.

### robust — Jackknife (leave-one-out) stability analysis of the Q1 ranking (Q1b).
`__all__`: `CONFIG_FACTORS`, `FAMILY_FACTORS`, `RANK_COLUMN`, `OUTPUT_COLUMNS`,
`jackknife_ranking`.

### selectors — Selector audit (Q2): do model-selection criteria pick accurate configs?
`__all__`: `ConfigScore`, `DEFAULT_SELECTORS`, `DEFAULT_STRATA`, `N_BOOT`,
`score_configs`, `audit`, `rigged_cases`, `coverage_under_misspecification`.
