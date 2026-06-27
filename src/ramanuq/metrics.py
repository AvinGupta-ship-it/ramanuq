"""Calibration-derived Raman metrics (I_D/I_G, L_a, n_D) with provenance wiring.

This module is deliberately free of hard-coded physical constants: every
calibration coefficient, wavelength convention, and stage-guard threshold is
read from ``data/calibrations/calibrations.yaml`` via :func:`load_calibrations`.

The intensity ratio fed into each calibration is chosen by the calibration's
own machine-readable ``intensity_kind`` field recorded in the YAML (exactly
``"area"`` or ``"height"``), never by hard-coding which calibration is which.
The verbose ``intensity_definition`` field is retained as documentation only.
``L_a`` (Cancado 2006) consumes the *area* ratio; ``n_D`` (Cancado 2011)
consumes the *height* ratio.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import yaml

from .lineshapes import lorentzian_height_from_area

# Required, must-be-non-empty provenance fields on every calibration entry.
_REQUIRED_FIELDS = (
    "citation",
    "doi",
    "validity",
    "intensity_definition",
    "intensity_kind",
)

# The only permitted non-calibration top-level key in the YAML.
_CONFIG_KEY = "stage_guard"

# Percentile bounds for bootstrap intervals (ordinary numbers, not constants).
_LO_PCT = 2.5
_HI_PCT = 97.5


# --------------------------------------------------------------------------- #
# Calibration loading + provenance validation
# --------------------------------------------------------------------------- #
def _parse_constant(entry_name, field_name, value):
    """Parse a calibration-constant string to float.

    ``"n/a"`` (case-insensitive) denotes 'no project constant' and is returned
    as ``None``.  Any other unparseable value raises -- never substitute a
    default.
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() == "n/a" or text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"calibration {entry_name!r}: {field_name} {value!r} "
            "does not parse to float"
        ) from exc


def load_calibrations(path):
    """Load and validate calibration provenance from a YAML file.

    Every top-level entry except ``stage_guard`` must be a calibration: it must
    contain a non-empty ``intensity_definition`` plus non-empty ``citation``,
    ``doi`` and ``validity``.  Constant strings are parsed to float (``"n/a"``
    means 'no project constant').  Raises :class:`ValueError`, naming the entry
    and field, on any missing/empty provenance or unparseable constant.
    """
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top-level YAML must be a mapping")

    out = {}
    for name, entry in raw.items():
        if name == _CONFIG_KEY:
            # Config block: loaded but exempt from provenance validation.
            out[name] = entry
            continue

        if not isinstance(entry, dict) or "intensity_definition" not in entry:
            raise ValueError(
                f"top-level entry {name!r} is not the permitted "
                f"{_CONFIG_KEY!r} config key and lacks 'intensity_definition'; "
                "every other top-level key must be a calibration"
            )

        for field_name in _REQUIRED_FIELDS:
            value = entry.get(field_name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                raise ValueError(
                    f"calibration {name!r} missing required field {field_name!r}"
                )

        parsed = dict(entry)
        if "constant_value" in entry:
            parsed["constant_value"] = _parse_constant(
                name, "constant_value", entry["constant_value"]
            )
        if "constant_uncertainty" in entry:
            parsed["constant_uncertainty"] = _parse_constant(
                name, "constant_uncertainty", entry["constant_uncertainty"]
            )
        out[name] = parsed

    return out


# --------------------------------------------------------------------------- #
# Metrics container
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Metrics:
    """Calibration-derived spectral metrics with bootstrap intervals.

    Interval fields are ``(lo, hi)`` percentile tuples; ``flags`` is a tuple of
    strings.  ``n_d_const_uncertainty`` is the *separate* multiplicative
    constant-uncertainty magnitude on ``n_d`` (distinct from ``n_d_interval``).
    """

    id_ig: float
    id_ig_interval: tuple
    la_tk: float
    la_cancado2006: float
    la_cancado2006_interval: tuple
    n_d: float
    n_d_interval: tuple
    n_d_const_uncertainty: float
    l_d: float
    flags: tuple


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _intensity_kind(entry):
    """Return a calibration's intensity routing kind from ``intensity_kind``.

    Reads the explicit machine-readable ``intensity_kind`` field, which must be
    exactly ``"area"`` or ``"height"`` (case-insensitive).  The verbose
    ``intensity_definition`` field is documentation only and is never parsed for
    routing.  Raises :class:`ValueError` if the field is missing or holds any
    other value.
    """
    value = entry.get("intensity_kind")
    if value is None:
        raise ValueError("calibration missing required field 'intensity_kind'")
    kind = str(value).strip().lower()
    if kind not in ("area", "height"):
        raise ValueError(
            f"intensity_kind {value!r} must be exactly 'area' or 'height'"
        )
    return kind


def _ratio_for(kind, area_ratio, height_ratio):
    """Select the area or height ratio for a calibration's declared kind."""
    return area_ratio if kind == "area" else height_ratio


def _percentile_interval(values):
    """``(2.5th, 97.5th)`` percentiles of finite ``values``; NaN-pair if empty."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(arr, _LO_PCT)), float(np.percentile(arr, _HI_PCT)))


def _boot_ratios(fit):
    """Per-bootstrap area and height ratio arrays from ``fit.bootstrap_df``."""
    boot = getattr(fit, "bootstrap_df", None)
    needed = ("D_area", "G_area", "D_fwhm", "G_fwhm")
    if boot is None or boot.empty or any(c not in boot.columns for c in needed):
        empty = np.array([], dtype=float)
        return empty, empty
    d_area = boot["D_area"].to_numpy(dtype=float)
    g_area = boot["G_area"].to_numpy(dtype=float)
    d_fwhm = boot["D_fwhm"].to_numpy(dtype=float)
    g_fwhm = boot["G_fwhm"].to_numpy(dtype=float)
    area_ratio = d_area / g_area
    height_ratio = (
        lorentzian_height_from_area(d_area, d_fwhm)
        / lorentzian_height_from_area(g_area, g_fwhm)
    )
    return area_ratio, height_ratio


# --------------------------------------------------------------------------- #
# Metric computation
# --------------------------------------------------------------------------- #
def compute_metrics(fit, calibrations, definition):
    """Compute :class:`Metrics` from a fit and loaded calibrations.

    ``definition`` (``"area"`` or ``"height"``) selects the ratio reported as
    ``id_ig``.  Each calibration consumes the ratio under *its own* declared
    intensity definition (read from the YAML), independent of ``definition``.
    """
    if definition not in ("area", "height"):
        raise ValueError(
            f"definition must be 'area' or 'height', got {definition!r}"
        )

    cal2006 = calibrations["cancado_2006"]
    cal2011 = calibrations["cancado_2011"]
    guard = calibrations[_CONFIG_KEY]

    c2006 = cal2006["constant_value"]
    c2011 = cal2011["constant_value"]
    c2011_unc = cal2011["constant_uncertainty"]
    lam = float(fit.meta["wavelength_nm"])

    # Routing kind each calibration declares (machine-readable YAML field).
    def2006 = _intensity_kind(cal2006)
    def2011 = _intensity_kind(cal2011)

    # Central ratios from the best-fit parameters.
    best = fit.best
    d_area = float(best["D_area"])
    g_area = float(best["G_area"])
    d_fwhm = float(best["D_fwhm"])
    g_fwhm = float(best["G_fwhm"])
    area_ratio = d_area / g_area
    height_ratio = (
        lorentzian_height_from_area(d_area, d_fwhm)
        / lorentzian_height_from_area(g_area, g_fwhm)
    )

    # Note: the area (integrated) and height definitions are distinct measures;
    # for the same spectrum they generally yield different I_D/I_G values.
    id_ig = area_ratio if definition == "area" else height_ratio

    # Bootstrap ratios under both definitions.
    area_ratio_boot, height_ratio_boot = _boot_ratios(fit)
    id_ig_boot = area_ratio_boot if definition == "area" else height_ratio_boot
    id_ig_interval = _percentile_interval(id_ig_boot)

    # --- L_a (Cancado 2006): lambda^4 in the NUMERATOR, area ratio inverted. --
    ratio_2006 = _ratio_for(def2006, area_ratio, height_ratio)
    la_cancado2006 = c2006 * (lam**4) * (ratio_2006 ** -1)
    ratio_2006_boot = _ratio_for(def2006, area_ratio_boot, height_ratio_boot)
    la_cancado2006_interval = _percentile_interval(
        c2006 * (lam**4) * (ratio_2006_boot ** -1)
    )

    # --- n_D (Cancado 2011): lambda^4 in the DENOMINATOR, height ratio. -------
    ratio_2011 = _ratio_for(def2011, area_ratio, height_ratio)
    n_d = (c2011 / (lam**4)) * ratio_2011
    ratio_2011_boot = _ratio_for(def2011, area_ratio_boot, height_ratio_boot)
    n_d_interval = _percentile_interval((c2011 / (lam**4)) * ratio_2011_boot)

    # Multiplicative, separate constant-uncertainty magnitude on n_D.
    n_d_const_uncertainty = n_d * (c2011_unc / c2011)

    # --- Intentional NaNs (no project constant / no recorded equation). -------
    la_tk = float("nan")
    l_d = float("nan")
    flags = ["tk_foundational_no_project_constant", "ld_equation_not_recorded"]

    # --- Stage guard. id_ig stays valid; calibrated quantities suppressed. ----
    g_fwhm_max = float(guard["g_fwhm_max_cm1"])
    d3_over_g_max = float(guard["d3_over_g_area_max"])

    guard_reasons = []
    if g_fwhm > g_fwhm_max:
        guard_reasons.append("stage2_guard:g_fwhm_exceeds_threshold")
    if "D3_area" in best:
        d3_over_g = float(best["D3_area"]) / g_area
        if d3_over_g > d3_over_g_max:
            guard_reasons.append("stage2_guard:d3_over_g_exceeds_threshold")

    if guard_reasons:
        nan = float("nan")
        nan_pair = (nan, nan)
        la_cancado2006 = nan
        la_cancado2006_interval = nan_pair
        n_d = nan
        n_d_interval = nan_pair
        n_d_const_uncertainty = nan
        la_tk = nan
        l_d = nan
        for reason in guard_reasons:
            flags.append(reason)
            warnings.warn(reason, stacklevel=2)

    return Metrics(
        id_ig=id_ig,
        id_ig_interval=id_ig_interval,
        la_tk=la_tk,
        la_cancado2006=la_cancado2006,
        la_cancado2006_interval=la_cancado2006_interval,
        n_d=n_d,
        n_d_interval=n_d_interval,
        n_d_const_uncertainty=n_d_const_uncertainty,
        l_d=l_d,
        flags=tuple(flags),
    )


__all__ = ["Metrics", "load_calibrations", "compute_metrics"]
