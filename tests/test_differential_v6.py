"""Differential test: main RamanUQ package vs. clean-room reference.

For 500 randomized valid inputs, each function in the main package must agree
with its independently-derived reference counterpart. Run inside the main
repository (where ``ramanuq`` is importable); the references live in
``refimpl/`` alongside this test tree.

Tolerances:
  * closed-form helper identities (height/area relations): rtol < 1e-9
  * full-array profile comparisons and the information criteria: rtol < 1e-6
"""

import os
import warnings

import numpy as np
import pytest

# Implementations under test (main package).
from ramanuq.lineshapes import lorentzian, gaussian, pseudo_voigt, bwf
from ramanuq.fit import aic, bic
from ramanuq.metrics import load_calibrations, compute_metrics
from ramanuq.mdc import mdc as pkg_mdc, to_delta_nd as pkg_to_delta_nd

# Clean-room references.
from refimpl.ref_lineshapes import (
    lorentzian as ref_lorentzian,
    gaussian as ref_gaussian,
    pseudo_voigt as ref_pseudo_voigt,
    bwf as ref_bwf,
    lorentzian_height_from_area as ref_lorentzian_height_from_area,
    lorentzian_area_from_height as ref_lorentzian_area_from_height,
    gaussian_height_from_area as ref_gaussian_height_from_area,
    gaussian_area_from_height as ref_gaussian_area_from_height,
)
from refimpl.ref_criteria import aic as ref_aic, bic as ref_bic
from refimpl.ref_metrics import (
    ref_load_calibrations,
    ref_id_ig_area,
    ref_id_ig_height,
    ref_la_cancado2006,
    ref_n_d_cancado2011,
    ref_n_d_const_uncertainty,
    ref_stage_guard,
)

RTOL_ANALYTIC = 1e-9
RTOL_NUMERIC = 1e-6
N_CASES = 500
SEED = 20240617

# Single calibration file feeds BOTH loaders (identical constants on each side).
CAL_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__), "..", "data", "calibrations", "calibrations.yaml"
    )
)
_PKG_CALS = load_calibrations(CAL_PATH)
_REF_CALS = ref_load_calibrations(CAL_PATH)

# Reference-side constants, read from the clean-room loader (no hard-coding).
C2006 = _REF_CALS["cancado_2006"]["constant_value"]
C2011 = _REF_CALS["cancado_2011"]["constant_value"]
C2011_UNC = _REF_CALS["cancado_2011"]["constant_uncertainty"]
G_FWHM_MAX = float(_REF_CALS["stage_guard"]["g_fwhm_max_cm1"])
D3_OVER_G_MAX = float(_REF_CALS["stage_guard"]["d3_over_g_area_max"])

# Package guard reasons are namespaced with this prefix; the clean-room guard
# emits the bare reason token. Strip it before comparing the reason set.
_GUARD_PREFIX = "stage2_guard:"


def _make_cases(rng):
    """Yield (center, area, height, fwhm, eta, q, x) tuples of valid inputs."""
    cases = []
    for _ in range(N_CASES):
        center = rng.uniform(1000.0, 1800.0)
        area = rng.uniform(0.5, 500.0)        # area > 0
        height = rng.uniform(0.5, 500.0)      # height > 0
        fwhm = rng.uniform(5.0, 200.0)        # G in a physical range
        eta = rng.uniform(0.0, 1.0)           # eta in [0, 1]
        # q away from 0: pick magnitude >= 0.5, random sign.
        q = rng.choice([-1.0, 1.0]) * rng.uniform(0.5, 20.0)
        # Sample x across a window spanning several FWHM around the center.
        x = center + rng.uniform(-6.0, 6.0, size=64) * fwhm
        cases.append((center, area, height, fwhm, eta, q, x))
    return cases


@pytest.mark.validation
def test_lorentzian_matches_reference():
    rng = np.random.default_rng(SEED)
    for center, area, _height, fwhm, _eta, _q, x in _make_cases(rng):
        got = lorentzian(x, center, area, fwhm)
        ref = ref_lorentzian(x, center, area, fwhm)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


@pytest.mark.validation
def test_gaussian_matches_reference():
    rng = np.random.default_rng(SEED + 1)
    for center, area, _height, fwhm, _eta, _q, x in _make_cases(rng):
        got = gaussian(x, center, area, fwhm)
        ref = ref_gaussian(x, center, area, fwhm)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


@pytest.mark.validation
def test_pseudo_voigt_matches_reference():
    rng = np.random.default_rng(SEED + 2)
    for center, area, _height, fwhm, eta, _q, x in _make_cases(rng):
        got = pseudo_voigt(x, center, area, fwhm, eta)
        ref = ref_pseudo_voigt(x, center, area, fwhm, eta)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


@pytest.mark.validation
def test_bwf_matches_reference():
    rng = np.random.default_rng(SEED + 3)
    for center, _area, height, fwhm, _eta, q, x in _make_cases(rng):
        got = bwf(x, center, height, fwhm, q)
        ref = ref_bwf(x, center, height, fwhm, q)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


@pytest.mark.validation
def test_lorentzian_peak_matches_analytic_height():
    """Closed-form identity: package Lorentzian peak == 2A/(pi*G) (rtol < 1e-9)."""
    rng = np.random.default_rng(SEED + 6)
    for center, area, _height, fwhm, _eta, _q, _x in _make_cases(rng):
        peak = lorentzian(np.array([center]), center, area, fwhm)[0]
        expected = ref_lorentzian_height_from_area(area, fwhm)
        np.testing.assert_allclose(peak, expected, rtol=RTOL_ANALYTIC, atol=0.0)
        # area_from_height is the exact inverse.
        np.testing.assert_allclose(
            ref_lorentzian_area_from_height(expected, fwhm),
            area,
            rtol=RTOL_ANALYTIC,
            atol=0.0,
        )


@pytest.mark.validation
def test_gaussian_peak_matches_analytic_height():
    """Closed-form identity: package Gaussian peak == (A/G)*sqrt(4ln2/pi)."""
    rng = np.random.default_rng(SEED + 7)
    for center, area, _height, fwhm, _eta, _q, _x in _make_cases(rng):
        peak = gaussian(np.array([center]), center, area, fwhm)[0]
        expected = ref_gaussian_height_from_area(area, fwhm)
        np.testing.assert_allclose(peak, expected, rtol=RTOL_ANALYTIC, atol=0.0)
        # area_from_height is the exact inverse.
        np.testing.assert_allclose(
            ref_gaussian_area_from_height(expected, fwhm),
            area,
            rtol=RTOL_ANALYTIC,
            atol=0.0,
        )


@pytest.mark.validation
def test_aic_matches_reference():
    rng = np.random.default_rng(SEED + 4)
    for _ in range(N_CASES):
        n = int(rng.integers(100, 600))
        k = int(rng.integers(1, 9))
        rss = rng.uniform(1e-3, 1e4)          # rss > 0
        got = aic(n, k, rss)
        ref = ref_aic(n, k, rss)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


@pytest.mark.validation
def test_bic_matches_reference():
    rng = np.random.default_rng(SEED + 5)
    for _ in range(N_CASES):
        n = int(rng.integers(100, 600))
        k = int(rng.integers(1, 9))
        rss = rng.uniform(1e-3, 1e4)          # rss > 0
        got = bic(n, k, rss)
        ref = ref_bic(n, k, rss)
        np.testing.assert_allclose(got, ref, rtol=RTOL_NUMERIC, atol=0.0)


# --------------------------------------------------------------------------- #
# Metrics differential (Gate V6 extension): ramanuq.metrics vs ref_metrics.
#
# The package exposes the metrics only through ``compute_metrics``; there are no
# standalone metric functions. We therefore build a minimal FitResult-like stub
# carrying ``best`` (the best-fit band parameters) and ``meta`` (wavelength), and
# feed the clean-room reference the identical scalars pulled from the same case.
# Both sides read the same calibration file, so the constants are identical.
# --------------------------------------------------------------------------- #
class _FitStub:
    """Minimal stand-in that ``compute_metrics`` accepts.

    ``compute_metrics`` reads ``fit.best``, ``fit.meta['wavelength_nm']`` and
    ``getattr(fit, 'bootstrap_df', None)``. With no bootstrap frame the interval
    fields come back NaN; this test never inspects intervals.
    """

    def __init__(self, best, wavelength_nm):
        self.best = best
        self.meta = {"wavelength_nm": wavelength_nm}
        self.bootstrap_df = None


def _make_band_case(rng, *, g_fwhm_lo, g_fwhm_hi):
    """One randomized valid set of band scalars (areas, FWHMs, wavelength)."""
    return {
        "D_area": rng.uniform(0.5, 500.0),     # area > 0
        "G_area": rng.uniform(0.5, 500.0),     # area > 0
        "D_fwhm": rng.uniform(5.0, 200.0),     # physical FWHM range
        "G_fwhm": rng.uniform(g_fwhm_lo, g_fwhm_hi),
        "wavelength_nm": rng.uniform(450.0, 650.0),  # visible excitation
    }


@pytest.mark.validation
def test_calibration_constants_match_reference():
    """Both loaders read the same file and yield the same float constants."""
    assert (
        _PKG_CALS["cancado_2006"]["constant_value"]
        == _REF_CALS["cancado_2006"]["constant_value"]
    )
    assert (
        _PKG_CALS["cancado_2011"]["constant_value"]
        == _REF_CALS["cancado_2011"]["constant_value"]
    )
    assert (
        _PKG_CALS["cancado_2011"]["constant_uncertainty"]
        == _REF_CALS["cancado_2011"]["constant_uncertainty"]
    )
    assert (
        float(_PKG_CALS["stage_guard"]["g_fwhm_max_cm1"])
        == float(_REF_CALS["stage_guard"]["g_fwhm_max_cm1"])
    )
    assert (
        float(_PKG_CALS["stage_guard"]["d3_over_g_area_max"])
        == float(_REF_CALS["stage_guard"]["d3_over_g_area_max"])
    )


@pytest.mark.validation
def test_id_ig_ratios_match_reference():
    """Area ratio and height ratio agree (closed-form, RTOL_ANALYTIC)."""
    rng = np.random.default_rng(SEED + 10)
    for _ in range(N_CASES):
        # Full physical G-FWHM range: id_ig is reported even when guarded.
        c = _make_band_case(rng, g_fwhm_lo=5.0, g_fwhm_hi=200.0)
        fit = _FitStub(
            {
                "D_area": c["D_area"],
                "G_area": c["G_area"],
                "D_fwhm": c["D_fwhm"],
                "G_fwhm": c["G_fwhm"],
            },
            c["wavelength_nm"],
        )
        m_area = compute_metrics(fit, _PKG_CALS, "area")
        m_height = compute_metrics(fit, _PKG_CALS, "height")

        ref_area = ref_id_ig_area(c["D_area"], c["G_area"])
        ref_height = ref_id_ig_height(
            c["D_area"], c["D_fwhm"], c["G_area"], c["G_fwhm"]
        )
        np.testing.assert_allclose(m_area.id_ig, ref_area, rtol=RTOL_ANALYTIC, atol=0.0)
        np.testing.assert_allclose(
            m_height.id_ig, ref_height, rtol=RTOL_ANALYTIC, atol=0.0
        )


@pytest.mark.validation
def test_calibrated_metrics_match_reference():
    """La, n_D and its constant-uncertainty agree (RTOL_NUMERIC).

    G-FWHM is held below the stage-2 threshold and no D3 area is supplied, so
    the calibrated quantities stay finite (un-suppressed) on both sides.
    """
    rng = np.random.default_rng(SEED + 11)
    for _ in range(N_CASES):
        c = _make_band_case(rng, g_fwhm_lo=5.0, g_fwhm_hi=G_FWHM_MAX - 0.1)
        lam = c["wavelength_nm"]
        fit = _FitStub(
            {
                "D_area": c["D_area"],
                "G_area": c["G_area"],
                "D_fwhm": c["D_fwhm"],
                "G_fwhm": c["G_fwhm"],
            },
            lam,
        )
        m = compute_metrics(fit, _PKG_CALS, "area")
        assert m.flags == (
            "tk_foundational_no_project_constant",
            "ld_equation_not_recorded",
        ), "case unexpectedly guarded; calibrated metrics would be NaN"

        # Reference ratios from the same scalars: La uses area, n_D uses height.
        area_ratio = ref_id_ig_area(c["D_area"], c["G_area"])
        height_ratio = ref_id_ig_height(
            c["D_area"], c["D_fwhm"], c["G_area"], c["G_fwhm"]
        )
        ref_la = ref_la_cancado2006(area_ratio, lam, C2006)
        ref_nd = ref_n_d_cancado2011(height_ratio, lam, C2011)
        ref_nd_unc = ref_n_d_const_uncertainty(ref_nd, C2011, C2011_UNC)

        np.testing.assert_allclose(
            m.la_cancado2006, ref_la, rtol=RTOL_NUMERIC, atol=0.0
        )
        np.testing.assert_allclose(m.n_d, ref_nd, rtol=RTOL_NUMERIC, atol=0.0)
        np.testing.assert_allclose(
            m.n_d_const_uncertainty, ref_nd_unc, rtol=RTOL_NUMERIC, atol=0.0
        )


# --------------------------------------------------------------------------- #
# Selector differential (Gate V6 extension): ramanuq.selectors vs ref_selectors.
#
# NOTE: ``refimpl/ref_selectors.py`` is authored by a SEPARATE blind session and
# copied in afterward. Until that file exists this test ERRORS on import (by
# design). The import is deferred into the test body so the error is isolated to
# this single test and does not take down the rest of the V6 differential suite.
# --------------------------------------------------------------------------- #
@pytest.mark.validation
def test_selectors_match_reference():
    """score_configs rho and top1_regret agree with the clean-room reference."""
    from ramanuq.selectors import score_configs
    from refimpl.ref_selectors import score_configs as ref_score_configs

    rng = np.random.default_rng(SEED + 20)
    for _ in range(N_CASES):
        n = int(rng.integers(4, 97))  # 4..96 configurations
        # Continuous draws -> no ties: argmin and rank order are unambiguous.
        selector_values = rng.uniform(-50.0, 50.0, size=n)
        abs_errors = rng.uniform(0.0, 5.0, size=n)

        got = score_configs(selector_values, abs_errors)
        ref = ref_score_configs(selector_values, abs_errors)

        np.testing.assert_allclose(
            got.rho, ref.rho, rtol=RTOL_NUMERIC, atol=1e-12
        )
        np.testing.assert_allclose(
            got.top1_regret, ref.top1_regret, rtol=RTOL_NUMERIC, atol=1e-12
        )


@pytest.mark.validation
def test_stage_guard_matches_reference():
    """Stage-2 guard decision + reason set agree exactly.

    G-FWHM straddles the threshold and the D3/G area ratio straddles its
    threshold; every third case omits D3 entirely (the None-D3 path).
    """
    rng = np.random.default_rng(SEED + 12)
    for i in range(N_CASES):
        c = _make_band_case(rng, g_fwhm_lo=20.0, g_fwhm_hi=60.0)  # straddles 40
        best = {
            "D_area": c["D_area"],
            "G_area": c["G_area"],
            "D_fwhm": c["D_fwhm"],
            "G_fwhm": c["G_fwhm"],
        }

        if i % 3 == 2:
            d3_or_none = None  # no D3 supplied -> guard skips the D3 check
        else:
            # D3/G area ratio straddles the 0.15 threshold.
            d3_or_none = rng.uniform(0.0, 0.30) * c["G_area"]
            best["D3_area"] = d3_or_none

        fit = _FitStub(best, c["wavelength_nm"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = compute_metrics(fit, _PKG_CALS, "area")

        pkg_reasons = {
            flag[len(_GUARD_PREFIX):]
            for flag in m.flags
            if flag.startswith(_GUARD_PREFIX)
        }
        pkg_triggered = bool(pkg_reasons)

        ref_triggered, ref_reasons = ref_stage_guard(
            c["G_fwhm"], c["G_area"], d3_or_none, G_FWHM_MAX, D3_OVER_G_MAX
        )

        assert pkg_triggered == ref_triggered
        assert pkg_reasons == set(ref_reasons)


# --------------------------------------------------------------------------- #
# MDC differential (Gate V6 extension): ramanuq.mdc vs ref_mdc.
#
# NOTE: ``refimpl/ref_mdc.py`` is authored by a SEPARATE blind session and copied
# in afterward. Until it exposes ``ref_mdc`` and ``ref_to_delta_nd`` these tests
# SKIP gracefully (importorskip on the module + an attribute guard), so the suite
# stays green. Once the reference lands they assert agreement to RTOL_ANALYTIC.
# --------------------------------------------------------------------------- #
def _ref_mdc_funcs():
    """Return (ref_mdc, ref_to_delta_nd) or skip if the reference is absent."""
    ref_mod = pytest.importorskip("refimpl.ref_mdc")
    ref_mdc = getattr(ref_mod, "ref_mdc", None)
    ref_to_delta_nd = getattr(ref_mod, "ref_to_delta_nd", None)
    if ref_mdc is None or ref_to_delta_nd is None:
        pytest.skip(
            "refimpl.ref_mdc not yet authored "
            "(ref_mdc/ref_to_delta_nd absent)"
        )
    return ref_mdc, ref_to_delta_nd


@pytest.mark.validation
def test_mdc_matches_reference():
    """mdc(sigma, alpha, power, n_rep) agrees with ref_mdc (RTOL_ANALYTIC)."""
    ref_mdc, _ = _ref_mdc_funcs()
    rng = np.random.default_rng(SEED + 30)
    for _ in range(N_CASES):
        sigma = rng.uniform(1e-3, 5.0)
        alpha = rng.uniform(0.001, 0.20)
        power = rng.uniform(0.50, 0.999)
        n_rep = int(rng.integers(1, 20))
        got = pkg_mdc(sigma, alpha=alpha, power=power, n_rep=n_rep)
        ref = ref_mdc(sigma, alpha=alpha, power=power, n_rep=n_rep)
        np.testing.assert_allclose(got, ref, rtol=RTOL_ANALYTIC, atol=0.0)


@pytest.mark.validation
def test_to_delta_nd_matches_reference():
    """Delta-n_D propagation agrees: src reads calibrations, ref gets the triple.

    Both sides see the SAME Cancado-2011 constant/uncertainty (one YAML file).
    The src function derives ``C_central/C_lo/C_hi = (const +/- unc) / lambda^4``
    internally from the calibrations object; the reference is fed that exact
    triple, extracted here from the same loaded calibrations.
    """
    ref_mdc, ref_to_delta_nd = _ref_mdc_funcs()
    const = _PKG_CALS["cancado_2011"]["constant_value"]
    unc = _PKG_CALS["cancado_2011"]["constant_uncertainty"]

    rng = np.random.default_rng(SEED + 31)
    for _ in range(N_CASES):
        mdc_value = rng.uniform(1e-4, 2.0)
        lam = rng.uniform(450.0, 650.0)  # visible excitation
        lam4 = lam ** 4
        c_central = const / lam4
        c_lo = (const - unc) / lam4
        c_hi = (const + unc) / lam4

        got = pkg_to_delta_nd(mdc_value, _PKG_CALS, lam)
        ref = ref_to_delta_nd(mdc_value, c_central, c_lo, c_hi)
        np.testing.assert_allclose(got, ref, rtol=RTOL_ANALYTIC, atol=0.0)
