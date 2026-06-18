"""Composite spectral models assembled from line shapes.

A model is a sum of named carbon-Raman bands, each rendered with a chosen line
shape.  Band identities (which peak is "D", "G", etc.) are fixed by nominal
anchor positions; these are *model structure*, not calibrations, and only seed
the bounds and the windowed-maxima initial guesses (centers are free to move
within +/-40 of the anchor).  The optional ``bwf_g`` flag renders the G band as
a Breit-Wigner-Fano profile instead of the default line shape.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from functools import reduce

import numpy as np
from lmfit import Model

from . import lineshapes


@dataclass(frozen=True)
class BandSpec:
    """Structural definition of one band."""

    name: str
    center: float  # nominal anchor position (cm^-1)
    fwhm_init: float
    fwhm_min: float
    fwhm_max: float


# Nominal anchor positions for disordered-carbon Raman bands.  These define
# which band is which; they are not calibration coefficients.
_BANDS = {
    "D": BandSpec("D", 1350.0, 50.0, 4.0, 300.0),
    "G": BandSpec("G", 1580.0, 40.0, 4.0, 300.0),
    "Dprime": BandSpec("Dprime", 1620.0, 20.0, 4.0, 60.0),
    "D3": BandSpec("D3", 1500.0, 120.0, 4.0, 300.0),
    "D4": BandSpec("D4", 1200.0, 100.0, 4.0, 300.0),
}

PEAK_SETS = {
    "DG": ["D", "G"],
    "DGDp": ["D", "G", "Dprime"],
    "DGDpD3D4": ["D", "G", "Dprime", "D3", "D4"],
}

_LINESHAPE_FUNCS = {
    "lorentzian": lineshapes.lorentzian,
    "gaussian": lineshapes.gaussian,
    "pseudo_voigt": lineshapes.pseudo_voigt,
}

_CENTER_WINDOW = 40.0  # center bound half-width
_GUESS_WINDOW = 35.0  # search half-width for windowed-maxima guesses
_DEFAULT_ETA = 0.5


def _area_from_height(lineshape, height, fwhm):
    """Initial area for an area-parameterized band of the given height."""
    if lineshape == "lorentzian":
        return lineshapes.lorentzian_area_from_height(height, fwhm)
    if lineshape == "gaussian":
        return lineshapes.gaussian_area_from_height(height, fwhm)
    if lineshape == "pseudo_voigt":
        return lineshapes.pseudo_voigt_area_from_height(height, fwhm, _DEFAULT_ETA)
    raise ValueError(f"unknown lineshape {lineshape!r}")


@dataclass
class SpectralModel:
    """An lmfit composite model plus the metadata needed to seed its params."""

    model: Model
    bands: list[BandSpec]
    lineshape: str
    bwf_g: bool

    def make_params(self):
        """Parameters at their nominal anchor defaults (bounds applied)."""
        return self.model.make_params()

    def _is_bwf(self, band):
        return self.bwf_g and band.name == "G"

    def guess(self, x, y):
        """Windowed-maxima initial guesses from baseline-corrected ``(x, y)``.

        For each band the largest value of ``y`` within +/-``_GUESS_WINDOW`` of
        the anchor seeds the center and amplitude.  Centers are kept inside the
        +/-``_CENTER_WINDOW`` bound.
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        params = self.make_params()

        for band in self.bands:
            prefix = f"{band.name}_"
            mask = np.abs(x - band.center) <= _GUESS_WINDOW
            if np.any(mask):
                idx = np.flatnonzero(mask)
                local = idx[np.argmax(y[idx])]
                center_guess = float(x[local])
                height_guess = float(max(y[local], 0.0))
            else:
                center_guess = band.center
                height_guess = 0.0

            lo = band.center - _CENTER_WINDOW
            hi = band.center + _CENTER_WINDOW
            params[f"{prefix}center"].set(value=min(max(center_guess, lo), hi))

            if self._is_bwf(band):
                params[f"{prefix}height"].set(value=max(height_guess, 1e-12))
            else:
                area_guess = _area_from_height(
                    self.lineshape, max(height_guess, 1e-12), band.fwhm_init
                )
                params[f"{prefix}area"].set(value=max(area_guess, 0.0))

        return params


def _make_band_model(band, lineshape, bwf):
    """Build one prefixed lmfit Model for a band."""
    prefix = f"{band.name}_"
    if bwf:
        return Model(lineshapes.bwf, prefix=prefix)
    return Model(_LINESHAPE_FUNCS[lineshape], prefix=prefix)


def build_model(peak_set, lineshape, bwf_g=False):
    """Assemble a bounded composite model.

    Parameters
    ----------
    peak_set:
        One of ``{"DG", "DGDp", "DGDpD3D4"}``.
    lineshape:
        One of ``{"lorentzian", "gaussian", "pseudo_voigt"}`` for all bands.
    bwf_g:
        If ``True``, render the G band as a Breit-Wigner-Fano profile.

    Returns
    -------
    SpectralModel
    """
    if peak_set not in PEAK_SETS:
        raise ValueError(
            f"unknown peak_set {peak_set!r}; expected one of {list(PEAK_SETS)}"
        )
    if lineshape not in _LINESHAPE_FUNCS:
        raise ValueError(
            f"unknown lineshape {lineshape!r}; expected one of {list(_LINESHAPE_FUNCS)}"
        )

    bands = [_BANDS[name] for name in PEAK_SETS[peak_set]]
    submodels = [
        _make_band_model(band, lineshape, bwf=(bwf_g and band.name == "G"))
        for band in bands
    ]
    composite = reduce(operator.add, submodels)

    for band in bands:
        prefix = f"{band.name}_"
        composite.set_param_hint(
            f"{prefix}center",
            value=band.center,
            min=band.center - _CENTER_WINDOW,
            max=band.center + _CENTER_WINDOW,
        )
        composite.set_param_hint(
            f"{prefix}fwhm",
            value=band.fwhm_init,
            min=band.fwhm_min,
            max=band.fwhm_max,
        )
        if bwf_g and band.name == "G":
            composite.set_param_hint(f"{prefix}height", value=1.0, min=0.0)
            # q stays negative (asymmetric G band) and bounded away from 0 so
            # the optimizer cannot drive the BWF 1/q term through a singularity.
            composite.set_param_hint(
                f"{prefix}q", value=-10.0, min=-100.0, max=-0.1
            )
        else:
            composite.set_param_hint(f"{prefix}area", value=1.0, min=0.0)
            if lineshape == "pseudo_voigt":
                composite.set_param_hint(
                    f"{prefix}eta", value=_DEFAULT_ETA, min=0.0, max=1.0
                )

    return SpectralModel(
        model=composite, bands=bands, lineshape=lineshape, bwf_g=bwf_g
    )
