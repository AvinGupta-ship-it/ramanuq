"""Validation tests for spectrum loading."""

import numpy as np
import pytest

from ramanuq.io import Spectrum, load_spectrum


def _valid_inputs():
    shift = np.linspace(1000, 2000, 100)
    intensity = np.random.default_rng(0).normal(size=100)
    return shift, intensity, 532.0


def test_load_valid_spectrum():
    shift, intensity, wl = _valid_inputs()
    spec = load_spectrum(shift, intensity, wl, meta={"sample": "x"})
    assert isinstance(spec, Spectrum)
    assert spec.wavelength_nm == 532.0
    assert spec.meta["sample"] == "x"


def test_non_monotonic_shift_raises():
    shift, intensity, wl = _valid_inputs()
    shift = shift.copy()
    shift[50] = shift[10]  # break strict monotonicity
    with pytest.raises(ValueError, match="monotonic"):
        load_spectrum(shift, intensity, wl)


def test_non_finite_values_raise():
    shift, intensity, wl = _valid_inputs()
    intensity = intensity.copy()
    intensity[3] = np.nan
    with pytest.raises(ValueError, match="finite"):
        load_spectrum(shift, intensity, wl)


def test_non_positive_wavelength_raises():
    shift, intensity, _ = _valid_inputs()
    with pytest.raises(ValueError, match="wavelength_nm"):
        load_spectrum(shift, intensity, -5.0)


def test_spectrum_is_frozen():
    shift, intensity, wl = _valid_inputs()
    spec = load_spectrum(shift, intensity, wl)
    with pytest.raises(Exception):
        spec.wavelength_nm = 488.0
