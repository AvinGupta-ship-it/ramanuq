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
