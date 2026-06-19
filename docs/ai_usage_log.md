# AI Usage Log

## 2026-06-18 — Day 2, Implementer (Session A) — DRAFT (unsigned)

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
