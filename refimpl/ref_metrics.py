"""Clean-room reference implementation of Raman calibration metrics.

This module is a CLEAN-ROOM REFERENCE implementation written solely from the
mathematical specification and the field schema of ``calibrations.yaml``. It
exists to provide an independent oracle for a differential test (Gate V6).

It is NOT production code and is NOT derived from, copied from, or informed by
any package source. In particular, it was written without viewing or
reconstructing any ``metrics.py`` file or any ``src/`` directory. No calibration
constant is hard-coded here; every constant is read from the calibration file
and parsed at load time.

Equations implemented (from the specification):
  * I_D/I_G by area:    A_D / A_G
  * I_D/I_G by height:  height = 2 * area / (pi * fwhm);  h_D / h_G
  * La (Cancado 2006):  La = c2006 * lambda^4 * (I_D/I_G)^-1     (lambda^4 numerator)
  * n_D (Cancado 2011): n_D = (c2011 / lambda^4) * (I_D/I_G)     (lambda^4 denominator)
  * n_D constant-uncertainty: n_D * (c2011_uncertainty / c2011)
  * stage guard from G FWHM and D3/G area thresholds
"""

from __future__ import annotations

import math
from typing import Optional

import yaml

# Provenance fields every calibration entry must carry (non-empty).
_REQUIRED_PROVENANCE = (
    "citation",
    "doi",
    "validity",
    "intensity_definition",
    "intensity_kind",
)

# Fields whose values are stored as strings but represent floats.
_CONSTANT_FIELDS = ("constant_value", "constant_uncertainty")


def ref_load_calibrations(path: str) -> dict:
    """Load and validate the calibration file.

    Top-level entries containing an ``intensity_definition`` field are
    calibrations; each must carry non-empty citation, doi, validity, and
    intensity_definition or a ValueError naming the entry and field is raised.

    ``stage_guard`` is a config entry (it has no ``intensity_definition``) and is
    exempt from provenance checks. Any other top-level entry lacking
    ``intensity_definition`` is an error.

    Calibration constant fields are stored as strings and are parsed to float.
    """
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError("calibration file did not parse to a mapping")

    result: dict = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{name}: entry is not a mapping")

        if "intensity_definition" not in entry:
            # Only stage_guard is permitted to lack provenance.
            if name == "stage_guard":
                result[name] = dict(entry)
                continue
            raise ValueError(
                f"{name}: missing intensity_definition (non-calibration entries "
                f"other than stage_guard are not allowed)"
            )

        # Calibration entry: validate provenance.
        for field in _REQUIRED_PROVENANCE:
            value = entry.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                raise ValueError(f"{name}: missing or empty required field '{field}'")

        parsed = dict(entry)
        for field in _CONSTANT_FIELDS:
            if field in parsed and parsed[field] is not None:
                # Numeric constants are stored as strings and parsed to float.
                # Documented non-numeric placeholders (e.g. "n/a" for the
                # foundational Tuinstra-Koenig entry, which gives no closed-form
                # constant) are left untouched.
                try:
                    parsed[field] = float(parsed[field])
                except (TypeError, ValueError):
                    pass
        result[name] = parsed

    return result


def ref_intensity_kind(entry: dict) -> str:
    """Read a calibration's machine-readable area/height routing kind.

    Returns ``"area"`` or ``"height"`` from the entry's ``intensity_kind`` field
    (case-insensitive). The prose ``intensity_definition`` field is documentation
    only and is not parsed for routing. Raises ValueError if the field is missing
    or carries any other value.
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


def ref_id_ig_area(d_area: float, g_area: float) -> float:
    """I_D/I_G defined by integrated band areas."""
    return d_area / g_area


def ref_id_ig_height(d_area: float, d_fwhm: float, g_area: float, g_fwhm: float) -> float:
    """I_D/I_G defined by Lorentzian peak heights.

    For a Lorentzian, peak height = 2 * area / (pi * fwhm).
    """
    d_height = 2.0 * d_area / (math.pi * d_fwhm)
    g_height = 2.0 * g_area / (math.pi * g_fwhm)
    return d_height / g_height


def ref_la_cancado2006(area_ratio: float, wavelength_nm: float, c2006: float) -> float:
    """Crystallite size La (Cancado 2006): lambda^4 in the numerator."""
    return c2006 * (wavelength_nm ** 4) * (area_ratio ** -1)


def ref_n_d_cancado2011(height_ratio: float, wavelength_nm: float, c2011: float) -> float:
    """Defect density n_D (Cancado 2011): lambda^4 in the denominator."""
    return (c2011 / (wavelength_nm ** 4)) * height_ratio


def ref_n_d_const_uncertainty(n_d: float, c2011: float, c2011_uncertainty: float) -> float:
    """Uncertainty in n_D propagated from the calibration constant alone."""
    return n_d * (c2011_uncertainty / c2011)


def ref_stage_guard(
    g_fwhm: float,
    g_area: float,
    d3_area_or_None: Optional[float],
    g_fwhm_max: float,
    d3_over_g_max: float,
) -> tuple[bool, list[str]]:
    """Detect stage-2-like spectra.

    Stage 2 if the G-band FWHM exceeds its threshold, or (only when a D3 area is
    provided) the D3/G area ratio exceeds its threshold. Returns a flag and the
    list of matching reason strings.
    """
    reasons: list[str] = []

    if g_fwhm > g_fwhm_max:
        reasons.append("g_fwhm_exceeds_threshold")

    if d3_area_or_None is not None:
        if d3_area_or_None / g_area > d3_over_g_max:
            reasons.append("d3_over_g_exceeds_threshold")

    return (len(reasons) > 0, reasons)
