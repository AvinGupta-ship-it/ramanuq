"""Tests for the calibration-derived metrics layer (Day 5).

The hand-pinned numeric expectations (532 nm, ratios == 1) are the user's
scientific decision; this file only encodes them.
"""

from __future__ import annotations

import copy
import math
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ramanuq.lineshapes import lorentzian_height_from_area
from ramanuq.metrics import Metrics, compute_metrics, load_calibrations

_REPO = Path(__file__).resolve().parents[1]
_CAL_PATH = _REPO / "data" / "calibrations" / "calibrations.yaml"
_METRICS_SRC = _REPO / "src" / "ramanuq" / "metrics.py"


# --------------------------------------------------------------------------- #
# Fixtures / fit builders
# --------------------------------------------------------------------------- #
def _make_fit(
    *,
    d_area,
    g_area,
    d_fwhm,
    g_fwhm,
    wavelength_nm=532.0,
    d3_area=None,
    boot_spread=0.0,
    n_boot=200,
    seed=0,
):
    """Build a minimal fit-like object exposing best/bootstrap_df/meta."""
    best = {
        "D_center": 1350.0,
        "D_area": float(d_area),
        "D_fwhm": float(d_fwhm),
        "G_center": 1580.0,
        "G_area": float(g_area),
        "G_fwhm": float(g_fwhm),
    }
    if d3_area is not None:
        best["D3_center"] = 1500.0
        best["D3_area"] = float(d3_area)
        best["D3_fwhm"] = 120.0

    cols = {"D_area": d_area, "G_area": g_area, "D_fwhm": d_fwhm, "G_fwhm": g_fwhm}
    if boot_spread > 0.0:
        rng = np.random.default_rng(seed)
        factors_d = rng.normal(1.0, boot_spread, size=n_boot)
        factors_g = rng.normal(1.0, boot_spread, size=n_boot)
        df = pd.DataFrame(
            {
                "D_area": d_area * factors_d,
                "G_area": g_area * factors_g,
                "D_fwhm": np.full(n_boot, d_fwhm),
                "G_fwhm": np.full(n_boot, g_fwhm),
            }
        )
    else:
        df = pd.DataFrame({k: [v] * n_boot for k, v in cols.items()})

    return types.SimpleNamespace(
        best=best, bootstrap_df=df, meta={"wavelength_nm": wavelength_nm}
    )


@pytest.fixture(scope="module")
def cals():
    return load_calibrations(_CAL_PATH)


# --------------------------------------------------------------------------- #
# Hand-pinned central values
# --------------------------------------------------------------------------- #
def test_handpin_la_and_nd(cals):
    # D_area == G_area and D_fwhm == G_fwhm => area ratio == height ratio == 1.0.
    fit = _make_fit(d_area=100.0, g_area=100.0, d_fwhm=30.0, g_fwhm=30.0)
    m = compute_metrics(fit, cals, "area")
    assert isinstance(m, Metrics)
    assert m.id_ig == pytest.approx(1.0, rel=1e-9)
    assert m.la_cancado2006 == pytest.approx(19.2246202982, rel=1e-3)
    assert m.n_d == pytest.approx(2.2471185038e11, rel=1e-3)


def test_handpin_const_uncertainty(cals):
    fit = _make_fit(d_area=100.0, g_area=100.0, d_fwhm=30.0, g_fwhm=30.0)
    m = compute_metrics(fit, cals, "area")
    assert m.n_d_const_uncertainty == pytest.approx(
        m.n_d * (0.5e22 / 1.8e22), rel=1e-3
    )


# --------------------------------------------------------------------------- #
# Intensity-definition wiring (area vs height must not be swapped)
# --------------------------------------------------------------------------- #
def test_intensity_definition_wiring(cals):
    # D_fwhm != G_fwhm => area ratio and height ratio differ.
    d_area, g_area, d_fwhm, g_fwhm = 2.0, 1.0, 10.0, 20.0
    fit = _make_fit(d_area=d_area, g_area=g_area, d_fwhm=d_fwhm, g_fwhm=g_fwhm)
    lam = 532.0
    c2006 = float(cals["cancado_2006"]["constant_value"])
    c2011 = float(cals["cancado_2011"]["constant_value"])

    area_ratio = d_area / g_area
    height_ratio = lorentzian_height_from_area(
        d_area, d_fwhm
    ) / lorentzian_height_from_area(g_area, g_fwhm)
    assert area_ratio != pytest.approx(height_ratio)

    m = compute_metrics(fit, cals, "area")
    # L_a (Cancado 2006) consumes the AREA ratio; n_D (2011) the HEIGHT ratio.
    assert m.la_cancado2006 == pytest.approx(c2006 * lam**4 / area_ratio, rel=1e-9)
    assert m.n_d == pytest.approx((c2011 / lam**4) * height_ratio, rel=1e-9)
    # If they were swapped these would instead match the other ratio.
    assert m.la_cancado2006 != pytest.approx(c2006 * lam**4 / height_ratio)
    assert m.n_d != pytest.approx((c2011 / lam**4) * area_ratio)


def test_intensity_kind_routes_area_and_height(cals):
    """Routing follows the machine-readable ``intensity_kind`` field.

    With distinct area and height ratios, La (2006, kind=area) must use the AREA
    ratio and n_D (2011, kind=height) the HEIGHT ratio (not swapped). Flipping
    the ``intensity_kind`` fields flips the routing, proving the selection is
    driven by that field rather than by which calibration is which.
    """
    d_area, g_area, d_fwhm, g_fwhm = 2.0, 1.0, 10.0, 20.0
    fit = _make_fit(d_area=d_area, g_area=g_area, d_fwhm=d_fwhm, g_fwhm=g_fwhm)
    lam = 532.0
    c2006 = float(cals["cancado_2006"]["constant_value"])
    c2011 = float(cals["cancado_2011"]["constant_value"])

    area_ratio = d_area / g_area
    height_ratio = lorentzian_height_from_area(
        d_area, d_fwhm
    ) / lorentzian_height_from_area(g_area, g_fwhm)
    assert area_ratio != pytest.approx(height_ratio)

    # Real YAML kinds: cancado_2006 = area, cancado_2011 = height.
    assert cals["cancado_2006"]["intensity_kind"].strip().lower() == "area"
    assert cals["cancado_2011"]["intensity_kind"].strip().lower() == "height"
    m = compute_metrics(fit, cals, "area")
    assert m.la_cancado2006 == pytest.approx(c2006 * lam**4 / area_ratio, rel=1e-9)
    assert m.n_d == pytest.approx((c2011 / lam**4) * height_ratio, rel=1e-9)

    # Flip the kinds: routing must follow the field, swapping the ratios used.
    swapped = copy.deepcopy(cals)
    swapped["cancado_2006"]["intensity_kind"] = "height"
    swapped["cancado_2011"]["intensity_kind"] = "area"
    m_sw = compute_metrics(fit, swapped, "area")
    assert m_sw.la_cancado2006 == pytest.approx(
        c2006 * lam**4 / height_ratio, rel=1e-9
    )
    assert m_sw.n_d == pytest.approx((c2011 / lam**4) * area_ratio, rel=1e-9)


# --------------------------------------------------------------------------- #
# Stage guard
# --------------------------------------------------------------------------- #
def test_stage_guard_fires_both_conditions(cals):
    guard = cals["stage_guard"]
    g_fwhm = guard["g_fwhm_max_cm1"] + 30.0  # broad G (stage-2-like)
    g_area = 100.0
    d3_area = (guard["d3_over_g_area_max"] + 0.15) * g_area  # > threshold
    fit = _make_fit(
        d_area=80.0, g_area=g_area, d_fwhm=50.0, g_fwhm=g_fwhm, d3_area=d3_area
    )
    with pytest.warns(UserWarning):
        m = compute_metrics(fit, cals, "area")

    assert math.isnan(m.la_cancado2006)
    assert math.isnan(m.la_tk)
    assert math.isnan(m.n_d)
    assert math.isnan(m.l_d)
    assert math.isnan(m.n_d_const_uncertainty)
    assert any(f.startswith("stage2_guard:") for f in m.flags)
    # id_ig stays valid through the guard.
    assert math.isfinite(m.id_ig)


def test_stage_guard_fires_g_only_no_d3(cals):
    guard = cals["stage_guard"]
    g_fwhm = guard["g_fwhm_max_cm1"] + 30.0
    fit = _make_fit(d_area=80.0, g_area=100.0, d_fwhm=50.0, g_fwhm=g_fwhm)
    with pytest.warns(UserWarning):
        m = compute_metrics(fit, cals, "area")
    assert math.isnan(m.n_d)
    assert "stage2_guard:g_fwhm_exceeds_threshold" in m.flags
    assert math.isfinite(m.id_ig)


def test_stage_guard_does_not_false_fire(cals):
    # Clean stage-1: G FWHM 22, no significant D3.
    fit = _make_fit(d_area=50.0, g_area=100.0, d_fwhm=40.0, g_fwhm=22.0)
    m = compute_metrics(fit, cals, "area")
    assert math.isfinite(m.la_cancado2006)
    assert math.isfinite(m.n_d)
    assert not any(f.startswith("stage2_guard:") for f in m.flags)


# --------------------------------------------------------------------------- #
# Provenance validation
# --------------------------------------------------------------------------- #
def _write_modified_yaml(tmp_path, mutate):
    raw = yaml.safe_load(_CAL_PATH.read_text())
    data = copy.deepcopy(raw)
    mutate(data)
    out = tmp_path / "calibrations.yaml"
    out.write_text(yaml.safe_dump(data))
    return out


def test_load_raises_on_missing_citation(tmp_path):
    path = _write_modified_yaml(
        tmp_path, lambda d: d["cancado_2006"].pop("citation")
    )
    with pytest.raises(ValueError, match="citation"):
        load_calibrations(path)


def test_load_raises_on_missing_doi(tmp_path):
    path = _write_modified_yaml(tmp_path, lambda d: d["cancado_2006"].pop("doi"))
    with pytest.raises(ValueError, match="doi"):
        load_calibrations(path)


def test_load_raises_on_missing_intensity_definition(tmp_path):
    path = _write_modified_yaml(
        tmp_path, lambda d: d["cancado_2006"].pop("intensity_definition")
    )
    with pytest.raises(ValueError):
        load_calibrations(path)


def test_load_raises_on_missing_intensity_kind(tmp_path):
    path = _write_modified_yaml(
        tmp_path, lambda d: d["cancado_2006"].pop("intensity_kind")
    )
    with pytest.raises(ValueError, match="intensity_kind"):
        load_calibrations(path)


# --------------------------------------------------------------------------- #
# No hard-coded calibration constants in the module source
# --------------------------------------------------------------------------- #
def test_no_hardcoded_constants():
    src = _METRICS_SRC.read_text()
    for literal in ("2.4e-10", "2.4-e10", "1.8e22", "0.5e22"):
        assert literal not in src, f"calibration literal {literal!r} hard-coded"


# --------------------------------------------------------------------------- #
# Interval sanity
# --------------------------------------------------------------------------- #
def test_interval_sanity(cals):
    fit = _make_fit(
        d_area=50.0, g_area=100.0, d_fwhm=40.0, g_fwhm=22.0, boot_spread=0.05
    )
    m = compute_metrics(fit, cals, "area")

    lo, hi = m.id_ig_interval
    assert lo <= m.id_ig <= hi

    la_lo, la_hi = m.la_cancado2006_interval
    assert la_lo <= m.la_cancado2006 <= la_hi

    nd_lo, nd_hi = m.n_d_interval
    assert nd_lo <= m.n_d <= nd_hi
