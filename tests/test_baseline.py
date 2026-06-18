"""Tests that all baseline methods return finite output."""

import numpy as np
import pytest

from ramanuq import baseline
from ramanuq.io import load_spectrum


def _spec():
    x = np.linspace(1000.0, 2000.0, 500)
    # Sloping background plus a couple of bumps.
    y = 0.01 * (x - 1000.0) + 5.0 * np.exp(-0.5 * ((x - 1350) / 30) ** 2)
    y += 8.0 * np.exp(-0.5 * ((x - 1580) / 25) ** 2)
    return load_spectrum(x, y, 532.0)


@pytest.mark.parametrize("method", ["linear", "poly3", "poly5", "als"])
def test_methods_return_finite(method):
    spec = _spec()
    base, diag = baseline.estimate(spec, method)
    assert base.shape == spec.intensity.shape
    assert np.all(np.isfinite(base))
    assert diag["method"] == method


def test_als_respects_overrides():
    spec = _spec()
    base, diag = baseline.estimate(spec, "als", lam=1e4, p=0.05, niter=5)
    assert diag["lam"] == 1e4
    assert diag["p"] == 0.05
    assert diag["niter"] == 5
    assert np.all(np.isfinite(base))


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="unknown baseline method"):
        baseline.estimate(_spec(), "wavelet")
