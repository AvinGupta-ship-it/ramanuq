"""Analytic spectral line-shape functions (Gaussian, Lorentzian, Voigt, BWF).

All peak shapes here are *area-parameterized* (the ``area`` argument is the true
integral of the peak over an infinite axis), except the Breit-Wigner-Fano (BWF)
profile, which is *height-parameterized* because its infinite-axis integral does
not converge.

Conventions
-----------
``fwhm`` is the full width at half maximum, in the same units as ``x``.
``center`` is the peak position.  All functions are vectorized in ``x``.
"""

from __future__ import annotations

import math

import numpy as np

# sigma = fwhm * _GAUSS_SIGMA_FACTOR  for a Gaussian.
_GAUSS_SIGMA_FACTOR = 1.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))
_SQRT_2PI = np.sqrt(2.0 * np.pi)

# Smallest |q| the BWF profile is evaluated at; below this we floor the
# magnitude (preserving sign) so dividing by q cannot produce inf/NaN.  The
# floor is far below any physically meaningful asymmetry, so it never changes
# results for q of practical size.
_BWF_Q_FLOOR = 1e-12


# --------------------------------------------------------------------------- #
# Lorentzian (area-parameterized)
# --------------------------------------------------------------------------- #
def lorentzian(x, center, area, fwhm):
    """Lorentzian whose integral over the whole axis equals ``area``."""
    x = np.asarray(x, dtype=float)
    hwhm = 0.5 * fwhm
    return area * (hwhm / np.pi) / ((x - center) ** 2 + hwhm**2)


def lorentzian_height_from_area(area, fwhm):
    """Peak height (value at ``center``) of an area-parameterized Lorentzian."""
    return 2.0 * area / (np.pi * fwhm)


def lorentzian_area_from_height(height, fwhm):
    """Area of a Lorentzian given its peak height and FWHM."""
    return 0.5 * np.pi * height * fwhm


# --------------------------------------------------------------------------- #
# Gaussian (area-parameterized)
# --------------------------------------------------------------------------- #
def gaussian(x, center, area, fwhm):
    """Gaussian whose integral over the whole axis equals ``area``."""
    x = np.asarray(x, dtype=float)
    sigma = fwhm * _GAUSS_SIGMA_FACTOR
    return area / (sigma * _SQRT_2PI) * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def gaussian_height_from_area(area, fwhm):
    """Peak height (value at ``center``) of an area-parameterized Gaussian."""
    sigma = fwhm * _GAUSS_SIGMA_FACTOR
    return area / (sigma * _SQRT_2PI)


def gaussian_area_from_height(height, fwhm):
    """Area of a Gaussian given its peak height and FWHM."""
    sigma = fwhm * _GAUSS_SIGMA_FACTOR
    return height * sigma * _SQRT_2PI


# --------------------------------------------------------------------------- #
# Pseudo-Voigt (area-parameterized, eta blends Lorentzian/Gaussian)
# --------------------------------------------------------------------------- #
def pseudo_voigt(x, center, area, fwhm, eta):
    """Linear blend ``eta*Lorentzian + (1-eta)*Gaussian``.

    Both components carry the full ``area`` and share ``fwhm``, so the total
    integral of the blend is exactly ``area``.  ``eta`` lies in ``[0, 1]``;
    ``eta=1`` is a pure Lorentzian and ``eta=0`` is a pure Gaussian.
    """
    return eta * lorentzian(x, center, area, fwhm) + (1.0 - eta) * gaussian(
        x, center, area, fwhm
    )


def pseudo_voigt_height_from_area(area, fwhm, eta):
    """Peak height of an area-parameterized pseudo-Voigt."""
    return eta * lorentzian_height_from_area(area, fwhm) + (
        1.0 - eta
    ) * gaussian_height_from_area(area, fwhm)


def pseudo_voigt_area_from_height(height, fwhm, eta):
    """Area of a pseudo-Voigt given its peak height, FWHM, and mixing ``eta``."""
    # height = area * (eta * h_L_unit + (1-eta) * h_G_unit), where h_*_unit is
    # the height of a unit-area component, so invert that linear relation.
    unit_height = eta * lorentzian_height_from_area(1.0, fwhm) + (
        1.0 - eta
    ) * gaussian_height_from_area(1.0, fwhm)
    return height / unit_height


# --------------------------------------------------------------------------- #
# Breit-Wigner-Fano (height-parameterized)
# --------------------------------------------------------------------------- #
def bwf(x, center, height, fwhm, q):
    """Breit-Wigner-Fano (Fano) profile, height-parameterized.

    Defined as ``height * [1 + 2(x-center)/(q*fwhm)]^2 / [1 + (2(x-center)/fwhm)^2]``.
    At ``x == center`` the value equals ``height``.  ``q`` is the asymmetry
    parameter; as ``|q| -> inf`` the profile tends to a Lorentzian of the same
    height and FWHM.  The infinite-axis integral does not converge, so there is
    deliberately no closed-form area helper for BWF.
    """
    x = np.asarray(x, dtype=float)
    t = 2.0 * (x - center) / fwhm
    # Floor a near-zero (or exactly zero) q to a tiny magnitude of the same
    # sign so the 1/q term stays finite; the formula is otherwise unchanged.
    q_safe = q if abs(q) >= _BWF_Q_FLOOR else math.copysign(_BWF_Q_FLOOR, q or 1.0)
    return height * (1.0 + t / q_safe) ** 2 / (1.0 + t**2)
