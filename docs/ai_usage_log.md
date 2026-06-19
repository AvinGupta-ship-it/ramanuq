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
