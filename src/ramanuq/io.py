"""Reading and validating Raman spectra and associated metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Spectrum:
    """An immutable single 1-D Raman spectrum.

    Attributes
    ----------
    shift:
        Raman shift axis (cm^-1), strictly monotonic.
    intensity:
        Intensity values, same length as ``shift``.
    wavelength_nm:
        Excitation wavelength in nanometres (strictly positive).
    meta:
        Free-form metadata dictionary.
    """

    shift: np.ndarray
    intensity: np.ndarray
    wavelength_nm: float
    meta: dict = field(default_factory=dict)


def load_spectrum(shift, intensity, wavelength_nm, meta=None):
    """Build and validate a :class:`Spectrum`.

    Each failure mode raises ``ValueError`` with a distinct, specific message:

    * non-finite values in ``shift`` or ``intensity``;
    * a ``shift`` axis that is not strictly monotonic;
    * a ``wavelength_nm`` that is not strictly positive (or not finite);
    * mismatched lengths of ``shift`` and ``intensity``.
    """
    shift = np.asarray(shift, dtype=float)
    intensity = np.asarray(intensity, dtype=float)

    if shift.ndim != 1 or intensity.ndim != 1:
        raise ValueError("shift and intensity must each be one-dimensional")

    if shift.shape != intensity.shape:
        raise ValueError(
            "shift and intensity must have the same length "
            f"(got {shift.shape[0]} and {intensity.shape[0]})"
        )

    if not np.all(np.isfinite(shift)) or not np.all(np.isfinite(intensity)):
        raise ValueError("shift and intensity must contain only finite values")

    diffs = np.diff(shift)
    if not (np.all(diffs > 0) or np.all(diffs < 0)):
        raise ValueError("shift axis must be strictly monotonic")

    if not (np.isfinite(wavelength_nm) and wavelength_nm > 0):
        raise ValueError("wavelength_nm must be a finite, strictly positive value")

    return Spectrum(
        shift=shift,
        intensity=intensity,
        wavelength_nm=float(wavelength_nm),
        meta=dict(meta) if meta is not None else {},
    )
