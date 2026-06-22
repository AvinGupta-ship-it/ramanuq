"""Tests for the Q1b jackknife stability analysis (P7).

Both fixtures are fabricated study frames with stability known by construction:
one configuration engineered to be unambiguously best in every applicable
resample (retention 1.0, no flip), and a near-tie engineered so a single
instance drop flips the rank-1 recommendation.  The assertions pin the
jackknife outputs to those known-by-construction answers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ramanuq.grid import RESULT_COLUMNS
from ramanuq.robust import jackknife_ranking


def _row(case_id, instance, baseline, lineshape, peak_set, id_ig, true):
    row = {c: np.nan for c in RESULT_COLUMNS}
    err = id_ig - true
    row.update(
        {
            "case_id": case_id,
            "stage_label": "stage1",
            "snr_label": 50,
            "severity": "none",
            "instance": instance,
            "material_class": "M",
            "baseline": baseline,
            "lineshape": lineshape,
            "bwf_g": False,
            "peak_set": peak_set,
            "intensity": "area",
            "id_ig": id_ig,
            "lo95": true - 1.0,   # wide -> coverage 1.0 (always eligible)
            "hi95": true + 1.0,
            "sigma_stat": 0.1,
            "n_failed": 0,
            "redchi": 1.0,
            "aic": 0.0,
            "bic": 0.0,
            "la": np.nan,
            "n_d": np.nan,
            "true_id_ig": true,
            "error": err,
            "abs_error": abs(err),
        }
    )
    return row


def _frame(rows):
    return pd.DataFrame(rows, columns=list(RESULT_COLUMNS))


# --------------------------------------------------------------------------- #
# Stable-by-construction: config A dominates in every applicable resample.
# --------------------------------------------------------------------------- #
def test_jackknife_stable_config():
    true = 1.0
    rows = []
    for i in range(3):
        # A: tiny error everywhere -> always best.
        rows.append(_row(f"A{i}", i, "als", "lorentzian", "DG", 1.01, true))
        # B: larger error everywhere -> always worse.
        rows.append(_row(f"B{i}", i, "poly3", "gaussian", "DG", 1.10, true))
    df = _frame(rows)

    out = jackknife_ranking(df)
    assert len(out) == 1
    rec = out.iloc[0]
    # The recommendation is A.
    assert rec["baseline"] == "als"
    assert rec["lineshape"] == "lorentzian"
    # Known-by-construction stability.
    assert rec["top_quartile_retention"] == 1.0
    assert rec["flip_flag"] is False or rec["flip_flag"] == False  # noqa: E712
    assert rec["rank_iqr"] == 0.0


# --------------------------------------------------------------------------- #
# Tie-by-construction: dropping instance 2 flips the rank-1 recommendation.
# --------------------------------------------------------------------------- #
def test_jackknife_flip_config():
    true = 1.0
    # A errors: i0=0.20, i1=0.20, i2=0.0 -> full RMSE 0.1633 (< B's 0.17).
    a_err = {0: 0.20, 1: 0.20, 2: 0.0}
    rows = []
    for i in range(3):
        rows.append(_row(f"A{i}", i, "als", "lorentzian", "DG",
                         true + a_err[i], true))
        # B: constant 0.17 error -> RMSE 0.17 everywhere.
        rows.append(_row(f"B{i}", i, "poly3", "gaussian", "DG",
                         true + 0.17, true))
    df = _frame(rows)

    out = jackknife_ranking(df)
    assert len(out) == 1
    rec = out.iloc[0]
    # Full-ranking winner is A (lower RMSE).
    assert rec["baseline"] == "als"
    # Dropping instance 2 makes B win -> a flip is recorded.
    assert rec["flip_flag"] is True or rec["flip_flag"] == True  # noqa: E712
    # 5 applicable resamples (drop B's baseline, drop B's lineshape, drop each
    # of 3 instances); A stays rank-1 in 4 of them -> retention 0.8.
    assert rec["n_resamples"] == 5
    assert rec["top_quartile_retention"] == pytest.approx(0.8)


def test_jackknife_uses_only_schema_columns():
    """Sanity: the T9 fragment exposes its declared output columns."""
    true = 1.0
    rows = []
    for i in range(3):
        rows.append(_row(f"A{i}", i, "als", "lorentzian", "DG", 1.01, true))
        rows.append(_row(f"B{i}", i, "poly3", "gaussian", "DG", 1.10, true))
    out = jackknife_ranking(_frame(rows))
    for col in ("top_quartile_retention", "rank_iqr", "flip_flag",
                "n_resamples"):
        assert col in out.columns
