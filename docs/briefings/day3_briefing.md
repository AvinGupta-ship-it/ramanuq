# Day 3 Science Briefing — Tier-A Synthetic Truth & Gate V1

**Date:** 2026-06-18 · **Topic:** synthetic ground truth and parameter recovery

## Why we generate synthetic spectra
To trust an I_D/I_G number on a *real* spectrum, we first have to prove the whole
pipeline can return the *right* number when we already know the answer. Synthetic
spectra are the only data where the truth is known exactly, because *we* built
them from analytic band functions. They let us separate "the method is correct"
from "the sample is messy."

## Where the truth comes from (and where it must NOT)
The pre-registered operational definition (validation_plan.md §2): true band
**area** is the integral of the generator's noiseless, baseline-free band
function; true band **height** is that function's maximum. Both are computed
**directly from the generator parameters** — never by fitting the curve and never
by reading a noisy/baselined array. If truth came from a fit, we'd be grading the
fitter against itself. Our line shapes are area-parameterized, so the `area`
argument *is* the analytic integral, and `*_height_from_area` gives the analytic
maximum.

## Both definitions, always labelled
I_D/I_G can mean a ratio of **areas** or a ratio of **heights**, and they are
*not* equal (they differ by the FWHM ratio). A bare "intensity" is ambiguous and
scientifically dangerous, so every truth record stores both, under the explicit
keys `true_id_ig_area` and `true_id_ig_height`.

## Tier A vs Tier B
**Tier A is *in-family*:** every band uses a shape the fitter can represent
exactly (Lorentzian or Gaussian). It isolates one question — given the *right*
model form, does the pipeline recover the parameters? **Tier B** (later) uses
shapes the fitter cannot match exactly (model misspecification), which is a
different, harder test. Mixing them would confound "can't fit" with "fit is
wrong."

## Matched recovery
Gate V1 fits each spectrum with the **matched** family and peak set — the same
band identities and shape the generator used — through the real
`fit_spectrum`/`PipelineConfig`, not a shortcut. On ideal (noise-free,
baseline-free) data a matched fit should return the truth to near machine
precision. Stage-1 here recovers I_D/I_G to ~1e-7 (gate is 1e-3).

## Determinism
Every stochastic choice (noise, optional spikes) derives from one project `SEED`.
Same seed ⇒ bit-for-bit identical spectra and truth. This makes the suite
auditable and every reported number reproducible.

## What Gate V1 proves — and what it does NOT
**Proves:** with the correct model form and clean data, the fitter + recovery
machinery is unbiased — there is no bug silently corrupting the extracted ratio.
**Does NOT prove:** anything about real spectra, noise robustness, baseline
removal on real backgrounds, model *misspecification* (Tier B), or selector
behaviour. A green V1 is necessary, not sufficient. (It is also why stage-2,
whose truth mixes Lorentzian and Gaussian bands that a single-lineshape fit
cannot represent, is intentionally outside V1's scope.)

---

## Quiz (no answers shown)

1. Our truth is computed from the analytic band functions, not from a fit to the
   generated curve. Give two distinct things that would go wrong if we instead
   defined "truth" as the result of fitting the noiseless spectrum.

2. A reviewer says "just store one I_D/I_G intensity per spectrum." Explain, with
   the relevant relationship, why the area ratio and the height ratio differ, and
   why storing only one is unsafe.

3. Gate V1 passes at 1e-3 for all stage-1 cases. A colleague concludes "the
   pipeline is validated for our real rGO spectra." State two specific reasons
   that conclusion is unjustified, and name one later gate that targets each gap.
