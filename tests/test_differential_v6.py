"""Differential test: main RamanUQ package vs. clean-room reference.

For 500 randomized valid inputs, each function in the main package must agree
with its independently-derived reference counterpart. Run inside the main
repository (where ``ramanuq`` is importable); the references live in
``refimpl/`` alongside this test tree.

Tolerances:
  * closed-form helper identities (height/area relations): rtol < 1e-9
  * full-array profile comparisons and the information criteria: rtol < 1e-6
"""

import numpy as np
import pytest

# Implementations under test (main package).
from ramanuq.lineshapes import lorentzian, gaussian, pseudo_voigt, bwf
from ramanuq.fit import aic, bic

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

RTOL_ANALYTIC = 1e-9
RTOL_NUMERIC = 1e-6
N_CASES = 500
SEED = 20240617


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
