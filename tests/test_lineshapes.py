"""Unit tests for analytic line-shape identities."""

import numpy as np
import pytest

from ramanuq import lineshapes as ls


@pytest.mark.parametrize("fwhm", [5.0, 20.0, 75.0])
@pytest.mark.parametrize("center", [0.0, 1350.0])
def test_lorentzian_height_and_fwhm(center, fwhm):
    area = 12.3
    height = ls.lorentzian_height_from_area(area, fwhm)
    # Height identity at the center.
    assert abs(ls.lorentzian(center, center, area, fwhm) - height) < 1e-8 * height
    # FWHM identity: half maximum exactly at center +/- fwhm/2.
    half = ls.lorentzian(center + fwhm / 2, center, area, fwhm)
    assert abs(half - height / 2) < 1e-6 * height


@pytest.mark.parametrize("fwhm", [5.0, 20.0, 75.0])
@pytest.mark.parametrize("center", [0.0, 1580.0])
def test_gaussian_height_and_fwhm(center, fwhm):
    area = 7.1
    height = ls.gaussian_height_from_area(area, fwhm)
    assert abs(ls.gaussian(center, center, area, fwhm) - height) < 1e-8 * height
    half = ls.gaussian(center + fwhm / 2, center, area, fwhm)
    assert abs(half - height / 2) < 1e-6 * height


@pytest.mark.parametrize("fwhm", [5.0, 20.0, 75.0])
def test_height_area_roundtrip(fwhm):
    # area -> height -> area recovers the original area to 1e-6 (relative).
    area = 3.7
    for area_from, height_from in (
        (ls.lorentzian_area_from_height, ls.lorentzian_height_from_area),
        (ls.gaussian_area_from_height, ls.gaussian_height_from_area),
    ):
        recovered = area_from(height_from(area, fwhm), fwhm)
        assert abs(recovered - area) < 1e-6 * area


def test_gaussian_area_integral():
    # Gaussian tails decay fast, so a finite grid integrates to the area.
    center, area, fwhm = 0.0, 5.0, 10.0
    x = np.linspace(-200, 200, 400001)
    integral = np.trapezoid(ls.gaussian(x, center, area, fwhm), x)
    assert abs(integral - area) < 1e-6 * area


def test_pseudo_voigt_total_area_height():
    fwhm, area, eta = 25.0, 4.0, 0.3
    height = ls.pseudo_voigt_height_from_area(area, fwhm, eta)
    assert abs(ls.pseudo_voigt(0.0, 0.0, area, fwhm, eta) - height) < 1e-8 * height
    recovered = ls.pseudo_voigt_area_from_height(height, fwhm, eta)
    assert abs(recovered - area) < 1e-6 * area


def test_pseudo_voigt_limiting_cases():
    x = np.linspace(-100, 100, 1001)
    center, area, fwhm = 5.0, 2.0, 18.0
    np.testing.assert_allclose(
        ls.pseudo_voigt(x, center, area, fwhm, 1.0),
        ls.lorentzian(x, center, area, fwhm),
        rtol=0,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        ls.pseudo_voigt(x, center, area, fwhm, 0.0),
        ls.gaussian(x, center, area, fwhm),
        rtol=0,
        atol=1e-12,
    )


def test_bwf_height_at_center_and_lorentzian_limit():
    center, height, fwhm = 1580.0, 9.0, 30.0
    assert abs(ls.bwf(center, center, height, fwhm, q=-12.0) - height) < 1e-8 * height
    # Large |q| -> Lorentzian of the same height and FWHM.
    x = np.linspace(center - 200, center + 200, 2001)
    lor = ls.lorentzian(x, center, ls.lorentzian_area_from_height(height, fwhm), fwhm)
    np.testing.assert_allclose(ls.bwf(x, center, height, fwhm, q=1e9), lor, atol=1e-4)
