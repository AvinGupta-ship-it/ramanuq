"""Baseline-method tests, including pre-registered Gate V2.

Gate V2 (validation_plan.md S1): baseline RMS error must be below **2% of the
G-band height**.  The frozen 2% tolerance is applied *in-class* per the V2 pairing
clarification (validation_plan.md, Avin Gupta 2026-06-18): each method is graded
only on backgrounds it is designed to represent.  ``linear`` is tested on the
``none`` baseline only (a straight line cannot represent a curved background, so
grading it on a cubic/curved background would measure the estimator's
mathematical limitation, not baseline-layer correctness).  ``poly3``, ``poly5``
and ``als`` are curved-baseline estimators and are graded on all three Tier-A
severities (``none``, ``mild_cubic``, ``strong_curved``), including severe
curvature.  The 2% threshold itself is unchanged from pre-registration.

The gate uses the explicitly-allowed *peak-free* truth construction: a noiseless
spectrum that is the Tier-A baseline curve with no peaks, so baseline-estimation
quality is isolated from peak confounding.  The reference G-band height is the
stage-1 analytic G height; the baseline amplitude is the stage-1 signal-relative
background a real Tier-A spectrum would carry.  No truth information beyond this
peak-free construction is used.
"""

import numpy as np
import pytest

from ramanuq import baseline, lineshapes, synth
from ramanuq.despike import despike
from ramanuq.io import load_spectrum

# --------------------------------------------------------------------------- #
# Gate V2 fixtures (peak-free, stage-1 reference)
# --------------------------------------------------------------------------- #
V2_TOL_FRAC = 0.02  # pre-registered: RMS error < 2% of G-band height (frozen)

# In-class method->baseline pairing (validation_plan.md V2 clarification).
_V2_PAIRS = [
    ("linear", "none"),
    ("poly3", "none"),
    ("poly3", "mild_cubic"),
    ("poly3", "strong_curved"),
    ("poly5", "none"),
    ("poly5", "mild_cubic"),
    ("poly5", "strong_curved"),
    ("als", "none"),
    ("als", "mild_cubic"),
    ("als", "strong_curved"),
]


def _stage1_reference():
    """Stage-1 grid, signal_max, and analytic G-band height (the V2 reference)."""
    peaks = synth._stage1_peaks(1.0)
    lo, hi, step = synth.GRID_NO_D4
    x = np.arange(lo, hi + 0.5 * step, step, dtype=float)
    signal_max = float(np.max(sum(synth._eval(p, x) for p in peaks)))
    g = next(p for p in peaks if p.name == "G")
    g_height = float(lineshapes.lorentzian_height_from_area(g.area, g.fwhm))
    return x, signal_max, g_height


def _peak_free_baseline_spectrum(label):
    """A noiseless, peak-free spectrum that is only the Tier-A baseline curve."""
    x, signal_max, g_height = _stage1_reference()
    true_baseline = synth._baseline_curve(label, x, signal_max)
    spec = load_spectrum(x, true_baseline.copy(), synth.WAVELENGTH_NM)
    return spec, true_baseline, g_height


@pytest.mark.validation
@pytest.mark.parametrize("method,label", _V2_PAIRS, ids=lambda v: v)
def test_v2_baseline_rms_below_2pct_of_g_height(method, label):
    """Gate V2: in-class baseline RMS error stays below 2% of the G-band height."""
    spec, true_baseline, g_height = _peak_free_baseline_spectrum(label)
    estimate, _diag = baseline.estimate(spec, method)
    rms = float(np.sqrt(np.mean((estimate - true_baseline) ** 2)))
    rel = rms / g_height
    assert rel < V2_TOL_FRAC, (
        f"V2 {method} on {label}: RMS {rel * 100:.3f}% of G height "
        f">= {V2_TOL_FRAC * 100:.0f}%"
    )


@pytest.mark.validation
def test_v2_covers_in_class_pairing():
    """Guard: the gate grades linear on `none` only; poly3/poly5/als on all three."""
    graded = {}
    for method, label in _V2_PAIRS:
        graded.setdefault(method, set()).add(label)
    assert graded["linear"] == {"none"}
    for m in ("poly3", "poly5", "als"):
        assert graded[m] == {"none", "mild_cubic", "strong_curved"}


# --------------------------------------------------------------------------- #
# Despiking must not distort clean (spike-free) data
# --------------------------------------------------------------------------- #
def test_despike_is_noop_on_clean_noisy_data():
    """On spike-free (noisy) data the despiker leaves every channel untouched.

    The despiker targets noisy spectra: its robust sigma is set by the noise, so
    genuine broad-band flanks sit well within the z threshold.  On spike-free
    input at a realistic SNR it must therefore be an exact no-op (and idempotent).
    """
    rng = np.random.default_rng(synth.SEED)
    x = np.linspace(1000.0, 1800.0, 801)
    sig = lineshapes.lorentzian(x, 1350.0, 1000.0, 35.0)
    sig = sig + lineshapes.lorentzian(x, 1585.0, 1000.0, 22.0)
    y = sig + rng.normal(0.0, float(sig.max()) / 50.0, x.size)  # SNR 50, no spikes

    once = despike(y, window=7, z_thresh=6.0)
    np.testing.assert_array_equal(once, y)  # exact no-op on spike-free input
    twice = despike(once, window=7, z_thresh=6.0)
    np.testing.assert_array_equal(twice, once)  # idempotent


def test_despike_is_noop_on_flat_input():
    """Constant (spike-free) input is returned unchanged."""
    y = np.full(64, 3.0)
    np.testing.assert_array_equal(despike(y), y)


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
