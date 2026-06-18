"""Gate V1 -- parameter recovery on noise-free, baseline-free Tier-A spectra.

Pre-registered gate (validation_plan.md S1): recovered parameters must agree with
the known generating parameters within **0.1% relative**.  Here that is applied
per-case to the I_D/I_G ratio, under *both* pre-registered truth definitions
(area and height), for every recovery spectrum -- not merely the mean.

Recovery goes through the real fitter (:func:`ramanuq.fit.fit_spectrum`); the test
never compares the generator to itself.  Two faithful pipeline choices are made
for the recovery path and documented inline:

* ``baseline_method="none"`` -- the recovery spectra are baseline-free by
  construction, so the correct background estimate is exactly zero.  Any
  estimating method (als/poly) removes ~0.02-6% of the band area and would bias
  the ratio above the 0.1% gate; ``none`` is the no-op subtraction added for
  exactly this already-corrected input.
* spike detection disabled (high ``despike_z``) -- the recovery spectra contain
  no cosmic spikes, and the default despiker would clip clean Lorentzian apexes.

After fitting, bands are identified by *nearest fitted center* to each true band
center.  This resolves lmfit's prefix-label permutation (the windowed-maxima
guess can seed D-prime and G onto the same position); the fitter still recovers
the true band areas, and identification-by-position is a standard, tolerance-
neutral step -- it does not weaken the gate.

Scope (approved): Gate V1 covers **stage-1 only** (in-family, all-Lorentzian
D/G/D-prime).  Stage-2 is excluded because its truth mixes Lorentzian D/G with
Gaussian D3/D4, while ``fit_spectrum`` applies a single lineshape to all bands:
no ``PipelineConfig`` can represent that spectrum, so a matched fit does not
exist.  Measured evidence for the scope boundary: even with a perfect (zero)
baseline, fitting stage-2 with the closest available config (DGDpD3D4,
Lorentzian) leaves a ~41% I_D/I_G residual.  The stage-2 spectra and truth are
still generated and committed for later coverage/baseline gates.
"""

from __future__ import annotations

import pytest

from ramanuq import lineshapes, synth
from ramanuq.fit import PipelineConfig, fit_spectrum
from ramanuq.model import PEAK_SETS

V1_TOL = 1e-3  # pre-registered 0.1% relative (frozen)
_NO_DESPIKE_Z = 1e12  # spike-free recovery data: do not clip clean peaks
_STAGE2_PERFECT_BASELINE_RESIDUAL = 0.41  # documented mixed-family floor


def _band_table(best, names):
    """Map each fitted band name to ``(center, area, fwhm)``."""
    return {n: (best[f"{n}_center"], best[f"{n}_area"], best[f"{n}_fwhm"]) for n in names}


def _nearest(bands, center):
    """The fitted band whose center is closest to ``center``."""
    return min(bands.values(), key=lambda b: abs(b[0] - center))


def _recovered_ratios(spec, peak_set, true_centers):
    """Fit ``spec`` with a matched Lorentzian config and return (area, height) I_D/I_G.

    Bands are identified by nearest fitted center to the true D and G centers.
    """
    names = list(PEAK_SETS[peak_set])
    cfg = PipelineConfig(
        peak_set=peak_set,
        lineshape="lorentzian",
        baseline_method="none",
        despike_z=_NO_DESPIKE_Z,
    )
    res = fit_spectrum(spec, cfg, n_boot=0, seed=synth.SEED)
    bands = _band_table(res.best, names)
    d = _nearest(bands, true_centers["D"])
    g = _nearest(bands, true_centers["G"])
    d_area, d_fwhm = d[1], d[2]
    g_area, g_fwhm = g[1], g[2]
    area_ratio = d_area / g_area
    height_ratio = lineshapes.lorentzian_height_from_area(
        d_area, d_fwhm
    ) / lineshapes.lorentzian_height_from_area(g_area, g_fwhm)
    return area_ratio, height_ratio, res.meta.get("success", False)


def _rel_err(recovered, true):
    """Relative error with a defensive zero-guard (no contracted case is zero)."""
    denom = abs(true)
    assert denom > 0, "true ratio is zero; Gate V1 denominator guard tripped"
    return abs(recovered - true) / denom


_STAGE1_RECOVERY = [c for c in synth.recovery_cases() if c.stage == 1]


@pytest.mark.validation
@pytest.mark.parametrize("case", _STAGE1_RECOVERY, ids=synth.case_id)
def test_v1_stage1_recovery_per_case(case):
    """Each stage-1 noise-free case recovers I_D/I_G within 0.1% (area AND height)."""
    spec, truth = synth.generate(case)
    true_centers = {p["name"]: p["center"] for p in truth["peaks"]}

    area_ratio, height_ratio, ok = _recovered_ratios(spec, "DGDp", true_centers)
    assert ok, f"primary fit failed for {truth['case_id']}"

    area_err = _rel_err(area_ratio, truth["true_id_ig_area"])
    height_err = _rel_err(height_ratio, truth["true_id_ig_height"])

    assert area_err < V1_TOL, (
        f"{truth['case_id']}: area I_D/I_G rel err {area_err:.3e} >= {V1_TOL}"
    )
    assert height_err < V1_TOL, (
        f"{truth['case_id']}: height I_D/I_G rel err {height_err:.3e} >= {V1_TOL}"
    )


@pytest.mark.validation
def test_v1_covers_every_stage1_recovery_case():
    """Guard: the gate is parametrized over all four stage-1 recovery cases."""
    assert len(_STAGE1_RECOVERY) == 4
    assert {c.ratio for c in _STAGE1_RECOVERY} == set(synth.STAGE1_RATIOS)


@pytest.mark.validation
def test_v1_stage2_excluded_with_documented_residual():
    """Document why stage-2 is out of V1 scope: mixed-family residual is large.

    This is not a recovery assertion -- it records the structural evidence that a
    single-lineshape fit cannot represent the mixed Lorentzian/Gaussian stage-2
    spectrum (so no matched fit exists), justifying the scope boundary.
    """
    (case,) = [c for c in synth.recovery_cases() if c.stage == 2]
    spec, truth = synth.generate(case)
    true_centers = {p["name"]: p["center"] for p in truth["peaks"]}
    area_ratio, _, ok = _recovered_ratios(spec, "DGDpD3D4", true_centers)
    assert ok
    residual = _rel_err(area_ratio, truth["true_id_ig_area"])
    # Far above the gate: confirms the mixed-family fit cannot recover stage-2.
    assert residual > 0.1, (
        "stage-2 mixed-family residual unexpectedly small; revisit V1 scope"
    )
