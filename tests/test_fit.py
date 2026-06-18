"""Tests for the fitting pipeline and information criteria."""

import numpy as np

from ramanuq import lineshapes
from ramanuq.fit import FitResult, PipelineConfig, aic, bic, fit_spectrum
from ramanuq.io import load_spectrum


def test_aic_bic_formulas():
    n, k, rss = 100, 4, 25.0
    assert np.isclose(aic(n, k, rss), n * np.log(rss / n) + 2 * k)
    assert np.isclose(bic(n, k, rss), n * np.log(rss / n) + k * np.log(n))


def _synthetic_dg():
    x = np.linspace(1100.0, 1750.0, 700)
    d = lineshapes.lorentzian(
        x, 1350.0, lineshapes.lorentzian_area_from_height(80.0, 60.0), 60.0
    )
    g = lineshapes.lorentzian(
        x, 1585.0, lineshapes.lorentzian_area_from_height(120.0, 40.0), 40.0
    )
    background = 20.0 + 0.02 * (x - 1100.0)
    rng = np.random.default_rng(7)
    y = background + d + g + rng.normal(scale=2.0, size=x.size)
    y[200] += 400.0  # cosmic-ray spike
    return load_spectrum(x, y, 532.0)


def test_fit_returns_stats_and_bootstrap():
    spec = _synthetic_dg()
    config = PipelineConfig(peak_set="DG", lineshape="lorentzian")
    result = fit_spectrum(spec, config, n_boot=30, seed=0)

    assert isinstance(result, FitResult)
    assert result.meta["success"] is True
    assert np.isfinite(result.redchi)
    assert np.isfinite(result.aic)
    assert np.isfinite(result.bic)
    assert isinstance(result.n_failed, int)
    assert 0 <= result.n_failed <= 30
    assert len(result.bootstrap_df) == 30 - result.n_failed

    # Recovered centers land near the truth.
    assert abs(result.best["D_center"] - 1350.0) < 15.0
    assert abs(result.best["G_center"] - 1585.0) < 15.0

    lo, hi = result.percentile_interval("G_center")
    assert lo <= result.best["G_center"] <= hi or np.isnan(lo)


def test_fit_never_raises_on_degenerate_input():
    # Flat spectrum: fitting may not converge, but must not raise.
    x = np.linspace(1100.0, 1750.0, 300)
    spec = load_spectrum(x, np.zeros_like(x), 532.0)
    config = PipelineConfig(peak_set="DG", lineshape="gaussian")
    result = fit_spectrum(spec, config, n_boot=5, seed=1)
    assert isinstance(result, FitResult)
    assert isinstance(result.n_failed, int)


def test_pseudo_voigt_and_bwf_configs_run():
    spec = _synthetic_dg()
    for config in (
        PipelineConfig(peak_set="DGDp", lineshape="pseudo_voigt"),
        PipelineConfig(peak_set="DG", lineshape="lorentzian", bwf_g=True),
    ):
        result = fit_spectrum(spec, config, n_boot=10, seed=2)
        assert isinstance(result, FitResult)
        assert result.n_failed <= 10
