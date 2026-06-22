"""Tests for the rolling-median despiker."""

import numpy as np

from ramanuq import lineshapes
from ramanuq.despike import despike


def _spectrum_with_spike():
    rng = np.random.default_rng(1)
    x = np.arange(0.0, 200.0)
    # A broad, genuine Raman peak that must survive despiking.
    peak = lineshapes.lorentzian(
        x, center=100.0, area=lineshapes.lorentzian_area_from_height(50.0, 15.0),
        fwhm=15.0,
    )
    baseline = 10.0 + 0.0 * x
    noise = rng.normal(scale=1.0, size=x.size)
    y = baseline + peak + noise
    clean = y.copy()
    # Inject a single-channel cosmic-ray spike well away from the peak.
    y[60] += 250.0
    return x, y, clean


def test_spike_removed_peak_survives():
    _, y, clean = _spectrum_with_spike()
    out = despike(y, window=7, z_thresh=6.0)
    # Spike at channel 60 is suppressed close to the clean baseline level.
    assert out[60] < 50.0
    assert abs(out[60] - clean[60]) < 10.0
    # The real peak apex region is preserved.
    apex = int(np.argmax(clean))
    assert abs(out[apex] - clean[apex]) < 5.0
    np.testing.assert_allclose(out[95:106], clean[95:106], atol=5.0)


def test_idempotent():
    _, y, _ = _spectrum_with_spike()
    once = despike(y, window=7, z_thresh=6.0)
    twice = despike(once, window=7, z_thresh=6.0)
    np.testing.assert_allclose(twice, once)


def test_flat_input_unchanged():
    y = np.full(50, 3.0)
    np.testing.assert_allclose(despike(y), y)
