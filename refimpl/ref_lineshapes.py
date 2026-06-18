"""Reference lineshape profiles, derived only from the math specification.

Conventions
-----------
``x``      : Raman shift (array-like)
``center`` : peak center x0
``area``   : integrated area A (for the area-normalized profiles)
``height`` : peak height (for BWF, and for the analytic height<->area helpers)
``fwhm``   : full width at half maximum parameter G (Gamma)

Spec equations
--------------
Lorentzian (area A):
    L(x) = (2A/pi) * G / [ 4*(x-x0)^2 + G^2 ]
Gaussian (area A):
    Gs(x) = (A/G) * sqrt(4*ln2/pi) * exp[ -4*ln2*(x-x0)^2 / G^2 ]
pseudo-Voigt:
    pV(x) = eta*L(x) + (1-eta)*Gs(x)   (both area-normalized to area A, same G)
Breit-Wigner-Fano (height I0):
    BWF(x) = I0 * [1 + 2*(x-x0)/(q*G)]^2 / [1 + (2*(x-x0)/G)^2]
"""

import numpy as np

# 4 * ln(2), appears throughout the Gaussian normalization.
_FOUR_LN2 = 4.0 * np.log(2.0)


def lorentzian(x, center, area, fwhm):
    """Area-normalized Lorentzian.

    L(x) = (2A/pi) * G / [4*(x-x0)^2 + G^2]
    """
    x = np.asarray(x, dtype=float)
    dx = x - center
    return (2.0 * area / np.pi) * fwhm / (4.0 * dx * dx + fwhm * fwhm)


def gaussian(x, center, area, fwhm):
    """Area-normalized Gaussian.

    Gs(x) = (A/G) * sqrt(4*ln2/pi) * exp[-4*ln2*(x-x0)^2 / G^2]
    """
    x = np.asarray(x, dtype=float)
    dx = x - center
    norm = (area / fwhm) * np.sqrt(_FOUR_LN2 / np.pi)
    return norm * np.exp(-_FOUR_LN2 * dx * dx / (fwhm * fwhm))


def pseudo_voigt(x, center, area, fwhm, eta):
    """pseudo-Voigt: eta*Lorentzian + (1-eta)*Gaussian, both with area A and G.

    eta = 1 -> pure Lorentzian, eta = 0 -> pure Gaussian. Total area = A.
    """
    return eta * lorentzian(x, center, area, fwhm) + (1.0 - eta) * gaussian(
        x, center, area, fwhm
    )


def bwf(x, center, height, fwhm, q):
    """Breit-Wigner-Fano profile (peak height I0 at center).

    BWF(x) = I0 * [1 + 2*(x-x0)/(q*G)]^2 / [1 + (2*(x-x0)/G)^2]

    Has no finite integral over an infinite axis; only the height parameter is
    meaningful as a normalization.
    """
    x = np.asarray(x, dtype=float)
    s = 2.0 * (x - center) / fwhm
    numer = (1.0 + s / q) ** 2
    denom = 1.0 + s * s
    return height * numer / denom


# ---------------------------------------------------------------------------
# Analytic height <-> area <-> FWHM relations.
#
# Lorentzian peak value at x = x0:
#     L(x0) = (2A/pi) * G / G^2 = 2A / (pi*G)
#   => height = 2A / (pi*G);   area = height * pi * G / 2
#
# Gaussian peak value at x = x0:
#     Gs(x0) = (A/G) * sqrt(4*ln2/pi)
#   => height = (A/G) * sqrt(4*ln2/pi);   area = height * G / sqrt(4*ln2/pi)
# ---------------------------------------------------------------------------


def lorentzian_height_from_area(area, fwhm):
    """Peak height of an area-A Lorentzian: 2A / (pi*G)."""
    return 2.0 * area / (np.pi * fwhm)


def lorentzian_area_from_height(height, fwhm):
    """Area of a Lorentzian given its peak height: height * pi * G / 2."""
    return height * np.pi * fwhm / 2.0


def gaussian_height_from_area(area, fwhm):
    """Peak height of an area-A Gaussian: (A/G) * sqrt(4*ln2/pi)."""
    return (area / fwhm) * np.sqrt(_FOUR_LN2 / np.pi)


def gaussian_area_from_height(height, fwhm):
    """Area of a Gaussian given its peak height: height * G / sqrt(4*ln2/pi)."""
    return height * fwhm / np.sqrt(_FOUR_LN2 / np.pi)
