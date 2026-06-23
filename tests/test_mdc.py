"""Unit tests for ramanuq.mdc (MDC formula + per-(config, regime) estimators).

The hand-pin test (a) is a human-supplied numeric anchor: it stays SKIPPED until
Avin inserts the hand-computed value. It is intentionally NOT a validation gate.
"""

import math

import numpy as np
import pandas as pd
import pytest

from ramanuq.mdc import (
    estimate_bias,
    estimate_sigma_single,
    mdc,
)

# --------------------------------------------------------------------------- #
# (a) Hand-pin #3 — human supplies the value; do NOT compute or fill it here.
# --------------------------------------------------------------------------- #
HAND_PIN_SIGMA = 0.10
HAND_PIN_MDC_IDIG = 0.396203


def test_hand_pin_mdc_idig():
    """Pin mdc() to Avin's independent hand computation (not a gate)."""
    if HAND_PIN_MDC_IDIG is None:
        pytest.skip("awaiting human hand-pin #3")
    assert math.isclose(
        mdc(HAND_PIN_SIGMA, alpha=0.05, power=0.8, n_rep=1),
        HAND_PIN_MDC_IDIG,
        abs_tol=1e-5,
    )


# --------------------------------------------------------------------------- #
# (b) 1/sqrt(n_rep) scaling.
# --------------------------------------------------------------------------- #
def test_mdc_scales_as_inverse_sqrt_n_rep():
    """mdc(sigma, n_rep=4) == mdc(sigma, n_rep=1) / 2 (since sqrt(4) == 2)."""
    sigma = 0.137
    assert math.isclose(
        mdc(sigma, n_rep=4),
        mdc(sigma, n_rep=1) / 2.0,
        rel_tol=1e-12,
    )


# --------------------------------------------------------------------------- #
# (c) estimate_sigma_single == std(ddof=1), estimate_bias == mean, on the
#     signed error column of a small fabricated frame with known values.
# --------------------------------------------------------------------------- #
def _fabricated_frame():
    """Two configs in one regime; the target config's errors are known."""
    rows = []
    target_errors = [0.1, -0.1, 0.3, -0.3, 0.2]
    for e in target_errors:
        rows.append(
            {
                "material_class": "synthetic_disordered_carbon",
                "snr_label": 50,
                "baseline": "linear",
                "lineshape": "lorentzian",
                "bwf_g": False,
                "peak_set": "DG",
                "intensity": "height",
                "error": e,
            }
        )
    # A decoy config in the same regime that must be filtered out.
    for e in [10.0, -10.0, 99.0]:
        rows.append(
            {
                "material_class": "synthetic_disordered_carbon",
                "snr_label": 50,
                "baseline": "als",
                "lineshape": "gaussian",
                "bwf_g": False,
                "peak_set": "DGDpD3D4",
                "intensity": "area",
                "error": e,
            }
        )
    return pd.DataFrame(rows), target_errors


def test_estimate_sigma_single_is_std_ddof1():
    df, target_errors = _fabricated_frame()
    config_class = {
        "baseline": "linear",
        "lineshape": "lorentzian",
        "bwf_g": False,
        "peak_set": "DG",
        "intensity": "height",
    }
    regime = {"material_class": "synthetic_disordered_carbon", "snr_label": 50}
    got = estimate_sigma_single(df, config_class, regime)
    expected = float(np.std(np.array(target_errors), ddof=1))
    assert math.isclose(got, expected, rel_tol=1e-12)


def test_estimate_bias_is_mean():
    df, target_errors = _fabricated_frame()
    config_class = {
        "baseline": "linear",
        "lineshape": "lorentzian",
        "bwf_g": False,
        "peak_set": "DG",
        "intensity": "height",
    }
    regime = {"material_class": "synthetic_disordered_carbon", "snr_label": 50}
    got = estimate_bias(df, config_class, regime)
    expected = float(np.mean(np.array(target_errors)))
    assert math.isclose(got, expected, rel_tol=1e-12)
