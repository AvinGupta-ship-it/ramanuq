"""Minimum detectable concentration / change (MDC) estimation.

This module is a thin, pure layer on top of the frozen grid study. It carries
NO hard-coded physical constants: the Cancado-2011 coefficient and its published
uncertainty are read from the loaded calibrations object (itself sourced from
``data/calibrations/calibrations.yaml`` via :func:`ramanuq.metrics.load_calibrations`).

Terms (see docs/validation_plan.md and the Day-8 briefing):

- :func:`mdc` returns the minimum detectable change in the *I_D/I_G* ratio from a
  single-measurement precision ``sigma_single``, using the standard two-sided
  detection-limit form ``(z_{1-alpha/2} + z_power) * sqrt(2) * sigma / sqrt(n_rep)``.
- :func:`to_delta_nd` propagates an MDC in *I_D/I_G* units into defect-density
  (``n_D``) units via the multiplicative Cancado-2011 relation, carrying the
  published constant uncertainty as a low/high band.
- :func:`estimate_sigma_single` is the per-(config, regime) PRECISION (sd of the
  signed error) and :func:`estimate_bias` is the SEPARATE accuracy term (mean of
  the signed error). Bias and precision are reported separately, never folded
  into one number.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

# The signed-error column produced by the truth join in ramanuq.grid.run_study.
_ERROR_COLUMN = "error"

# Name of the Cancado-2011 calibration entry in the loaded YAML object.
_CANCADO2011_KEY = "cancado_2011"


def mdc(sigma_single: float, alpha: float = 0.05, power: float = 0.8,
        n_rep: int = 1) -> float:
    """Minimum detectable change in *I_D/I_G* from single-measurement precision.

    ``(norm.ppf(1 - alpha/2) + norm.ppf(power)) * sqrt(2) * sigma_single /
    sqrt(n_rep)``. The two z-values are the two-sided false-positive control
    ``z_{1-alpha/2}`` and the one-sided power term ``z_power``; ``sqrt(2)``
    accounts for differencing two independent measurements; ``1/sqrt(n_rep)``
    is the precision gain from averaging ``n_rep`` replicates.
    """
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z_power = norm.ppf(power)
    return (z_alpha + z_power) * math.sqrt(2.0) * sigma_single / math.sqrt(n_rep)


def to_delta_nd(mdc_value: float, calibrations,
                wavelength_nm: float) -> tuple[float, float, float]:
    """Propagate an *I_D/I_G* MDC into defect-density (``n_D``) units.

    Reads the Cancado-2011 coefficient and its PUBLISHED uncertainty from the
    loaded ``calibrations`` object (never a hard-coded number). The wavelength-
    specific constant is ``C(lambda) = constant_value / wavelength_nm**4`` so
    that ``n_D = C * (I_D/I_G)`` is multiplicative, matching the published
    relation ``n_D = [const / lambda^4] * (I_D/I_G)``.

    Returns ``(central, lo, hi)`` where ``central = C_central * mdc_value`` and
    ``lo``/``hi`` use ``C_central -/+ published_uncertainty / lambda^4``. Raises
    :class:`ValueError` if the Cancado-2011 entry lacks the uncertainty field
    (we never guess it).
    """
    entry = calibrations[_CANCADO2011_KEY]
    const = entry.get("constant_value")
    unc = entry.get("constant_uncertainty")
    if const is None:
        raise ValueError(
            f"calibration {_CANCADO2011_KEY!r} missing 'constant_value'"
        )
    if unc is None:
        raise ValueError(
            f"calibration {_CANCADO2011_KEY!r} missing 'constant_uncertainty'; "
            "Delta-n_D propagation needs the published constant uncertainty"
        )

    lam4 = float(wavelength_nm) ** 4
    c_central = float(const) / lam4
    c_lo = (float(const) - float(unc)) / lam4
    c_hi = (float(const) + float(unc)) / lam4

    return (c_central * mdc_value, c_lo * mdc_value, c_hi * mdc_value)


def _filter(study_df, config_class, regime):
    """Rows of ``study_df`` matching the given config and regime selectors.

    Both ``config_class`` and ``regime`` are mappings ``{column: value}``; every
    supplied key is matched by equality. ``config_class`` keys come from the 5
    configuration DOF; ``regime`` keys are ``material_class`` and/or
    ``snr_label``.
    """
    mask = np.ones(len(study_df), dtype=bool)
    for column, value in dict(config_class).items():
        mask &= study_df[column].to_numpy() == value
    for column, value in dict(regime).items():
        mask &= study_df[column].to_numpy() == value
    return study_df[mask]


def _finite_errors(study_df, config_class, regime):
    sub = _filter(study_df, config_class, regime)
    err = sub[_ERROR_COLUMN].to_numpy(dtype=float)
    return err[np.isfinite(err)]


def estimate_sigma_single(study_df, config_class, regime) -> float:
    """PRECISION: sample sd (ddof=1) of the signed error for a (config, regime).

    Filters ``study_df`` to ``config_class`` (the configuration DOF) and
    ``regime`` (``material_class`` + ``snr_label``) and returns the standard
    deviation of the finite signed ``error`` values. ``nan`` if fewer than two
    finite errors are present.
    """
    err = _finite_errors(study_df, config_class, regime)
    if err.size < 2:
        return float("nan")
    return float(np.std(err, ddof=1))


def estimate_bias(study_df, config_class, regime) -> float:
    """ACCURACY (reported SEPARATELY): mean of the signed error for a (config, regime).

    Same filter as :func:`estimate_sigma_single`; returns the mean of the finite
    signed ``error`` values. ``nan`` if no finite errors are present.
    """
    err = _finite_errors(study_df, config_class, regime)
    if err.size == 0:
        return float("nan")
    return float(np.mean(err))


__all__ = [
    "mdc",
    "to_delta_nd",
    "estimate_sigma_single",
    "estimate_bias",
]
