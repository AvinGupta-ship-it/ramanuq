"""Contract tests for :func:`ramanuq.model.build_model`.

These assert the contracted parameter bounds and the windowed-maxima initial
guesses *independently* of the implementation's own constants: the anchors,
center window, and FWHM ranges are restated here so the tests fail if the
implementation drifts from the documented contract.
"""

import numpy as np
import pytest

from ramanuq import lineshapes
from ramanuq.model import PEAK_SETS, build_model

# Contracted anchors and FWHM ranges (cm^-1).  Restated here, not imported.
ANCHORS = {
    "D": 1350.0,
    "G": 1580.0,
    "Dprime": 1620.0,
    "D3": 1500.0,
    "D4": 1200.0,
}
CENTER_WINDOW = 40.0  # centers must stay within +/- this of the anchor
FWHM_RANGE = {  # (min, max) per band
    "D": (4.0, 300.0),
    "G": (4.0, 300.0),
    "Dprime": (4.0, 60.0),
    "D3": (4.0, 300.0),
    "D4": (4.0, 300.0),
}

PEAK_SET_NAMES = list(PEAK_SETS)  # "DG", "DGDp", "DGDpD3D4"


@pytest.mark.parametrize("peak_set", PEAK_SET_NAMES)
def test_build_model_bounds_contract(peak_set):
    """Each band exposes the contracted center, FWHM, and area bounds."""
    sm = build_model(peak_set, "lorentzian")
    params = sm.make_params()
    band_names = PEAK_SETS[peak_set]

    for name in band_names:
        anchor = ANCHORS[name]

        # Centers bounded within +/- CENTER_WINDOW of the anchor.
        center = params[f"{name}_center"]
        assert center.min == pytest.approx(anchor - CENTER_WINDOW)
        assert center.max == pytest.approx(anchor + CENTER_WINDOW)
        assert anchor - CENTER_WINDOW <= center.value <= anchor + CENTER_WINDOW

        # FWHM bounded within its contracted range ([4, 60] for D-prime).
        fwhm = params[f"{name}_fwhm"]
        lo, hi = FWHM_RANGE[name]
        assert fwhm.min == pytest.approx(lo)
        assert fwhm.max == pytest.approx(hi)
        assert lo <= fwhm.value <= hi

        # Areas are non-negative.
        area = params[f"{name}_area"]
        assert area.min == pytest.approx(0.0)
        assert area.value >= 0.0


def test_dprime_fwhm_is_narrower_than_broad_bands():
    """The D-prime upper FWHM bound is the narrow 60, not the broad 300."""
    params = build_model("DGDp", "lorentzian").make_params()
    assert params["Dprime_fwhm"].max == pytest.approx(60.0)
    assert params["G_fwhm"].max == pytest.approx(300.0)


def test_bwf_g_q_bounded_away_from_zero():
    """The BWF G-band asymmetry q is negative and cannot reach 0."""
    params = build_model("DG", "lorentzian", bwf_g=True).make_params()
    q = params["G_q"]
    assert q.max < 0.0  # stays negative -> never crosses through 0
    assert q.min < q.max
    assert q.min <= q.value <= q.max


def _synthetic_spectrum(peak_set, offsets):
    """Baseline-free (x, y) with one bump per band, offset from each anchor."""
    x = np.linspace(1100.0, 1700.0, 1201)
    y = np.zeros_like(x)
    for name in PEAK_SETS[peak_set]:
        center = ANCHORS[name] + offsets.get(name, 0.0)
        area = lineshapes.lorentzian_area_from_height(100.0, 20.0)
        y = y + lineshapes.lorentzian(x, center, area, 20.0)
    return x, y


@pytest.mark.parametrize("peak_set", PEAK_SET_NAMES)
def test_guess_centers_fall_within_allowed_windows(peak_set):
    """Windowed-maxima guesses land inside each band's +/- CENTER_WINDOW."""
    # Offset each true peak within the guess search window (< 35 cm^-1).
    offsets = {"D": 12.0, "G": -8.0, "Dprime": 10.0, "D3": -15.0, "D4": 20.0}
    x, y = _synthetic_spectrum(peak_set, offsets)

    sm = build_model(peak_set, "lorentzian")
    params = sm.guess(x, y)

    for name in PEAK_SETS[peak_set]:
        anchor = ANCHORS[name]
        center = params[f"{name}_center"].value
        assert anchor - CENTER_WINDOW <= center <= anchor + CENTER_WINDOW
        # Areas seeded from observed height stay non-negative.
        assert params[f"{name}_area"].value >= 0.0
