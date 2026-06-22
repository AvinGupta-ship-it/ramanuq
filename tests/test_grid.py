"""Tests for the configuration-grid study (P6): grid build, schema, ranking,
descriptive decomposition, Gate V3, and the RESULT_COLUMNS schema freeze.

Gate V3 tolerance is pinned here as a named constant citing the frozen plan;
the science (tolerance, slice, class factors) is read from, not invented by,
this test.
"""

from __future__ import annotations

import ast
import os
import warnings

import numpy as np
import pandas as pd
import pytest

from ramanuq import grid, robust
from ramanuq.grid import RESULT_COLUMNS

# --------------------------------------------------------------------------- #
# Gate V3 tolerance: docs/validation_plan.md Section 1 ("V3 - Hostile-spectrum
# bias: at least one configuration class must achieve mean absolute bias below
# 5% on stage-1 hostile spectra at SNR 50").  Pinned, not invented.
# --------------------------------------------------------------------------- #
V3_BIAS_TOL = 0.05

_TIERB_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "synthetic", "tierB"
)


# --------------------------------------------------------------------------- #
# Grid construction
# --------------------------------------------------------------------------- #
def test_default_grid_size_and_factor_levels():
    cfgs = grid.default_grid()
    # 4 baselines x [(lineshape,bwf): lor(F,T)+gauss(F)+pv(F) = 4] x 3 peak_set
    # x 2 intensity = 96.
    assert len(cfgs) == 96
    # No duplicate configurations.
    keys = {tuple(sorted(c.items())) for c in cfgs}
    assert len(keys) == 96


def test_bwf_only_with_lorentzian():
    for c in grid.default_grid():
        if c["bwf_g"]:
            assert c["lineshape"] == "lorentzian"
    # bwf_g=True must never appear for gaussian / pseudo_voigt.
    assert not any(
        c["bwf_g"] and c["lineshape"] in ("gaussian", "pseudo_voigt")
        for c in grid.default_grid()
    )


def test_run_grid_returns_exact_schema():
    spectra, _truth = grid._load_tierB_suite(_TIERB_DIR)
    spec = spectra[0]
    subset = grid.default_grid()[:3]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = grid.run_grid([spec], configs=subset, n_boot=0)
    # Columns are EXACTLY RESULT_COLUMNS, in order.
    assert tuple(df.columns) == RESULT_COLUMNS
    assert len(df) == 3
    # n_failed (the failure-rate column) is present and integer-valued.
    assert "n_failed" in df.columns
    assert df["n_failed"].notna().all()


# --------------------------------------------------------------------------- #
# Descriptive (non-causal) decomposition
# --------------------------------------------------------------------------- #
def test_decompose_is_labelled_descriptive():
    df = _toy_results()
    out = grid.decompose(df)
    assert "DESCRIPTIVE" in out["label"]
    assert "DESCRIPTIVE" in grid.decompose.__doc__
    # Per-factor level means exist for each of the 5 factors.
    for factor in ("baseline", "lineshape", "bwf_g", "peak_set", "intensity"):
        assert factor in out["per_factor"]


# --------------------------------------------------------------------------- #
# Ranking rule (Section 3): RMSE order with coverage/failure eligibility gates
# --------------------------------------------------------------------------- #
def test_rank_excludes_low_coverage_not_ranks_last():
    rows = []
    # Config A: best RMSE but coverage below floor -> EXCLUDED.
    for i in range(10):
        rows.append(
            _result_row("A", i, "als", "lorentzian", False, "DG", "area",
                        id_ig=1.001, true=1.0, covered=(i == 0))  # 10% coverage
        )
    # Config B: worse RMSE but full coverage -> eligible, becomes rank 1.
    for i in range(10):
        rows.append(
            _result_row("B", i, "poly3", "gaussian", False, "DG", "area",
                        id_ig=1.05, true=1.0, covered=True)
        )
    df = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    ranked = grid.rank_configurations(df)
    # A is excluded entirely (not present), B is the only ranked survivor.
    assert set(ranked["baseline"]) == {"poly3"}
    assert ranked.iloc[0]["rank"] == 1


def test_rank_excludes_high_failure_rate():
    rows = []
    for i in range(10):
        # Half the fits fail -> failure rate 0.5 > 0.05 -> excluded.
        idig = np.nan if i % 2 == 0 else 1.001
        rows.append(
            _result_row("A", i, "als", "lorentzian", False, "DG", "area",
                        id_ig=idig, true=1.0, covered=True)
        )
    for i in range(10):
        rows.append(
            _result_row("B", i, "poly3", "gaussian", False, "DG", "area",
                        id_ig=1.05, true=1.0, covered=True)
        )
    df = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    ranked = grid.rank_configurations(df)
    assert set(ranked["baseline"]) == {"poly3"}


# --------------------------------------------------------------------------- #
# Gate V3 (pre-registered validation gate)
# --------------------------------------------------------------------------- #
@pytest.mark.validation
def test_gate_v3_hostile_bias():
    """At least one configuration class clears mean |bias| < V3_BIAS_TOL on the
    mechanically-selected stage-1 SNR-50 Tier-B slice.

    Class key is (lineshape, baseline, peak_set, intensity): bias is graded per
    intensity definition because the area-ratio and height-ratio truths are
    distinct physical quantities and must not be pooled.  Bias = |mean signed
    error| (systematic offset), per the pre-registered "mean absolute bias".
    """
    spectra, truth = grid._load_tierB_suite(_TIERB_DIR)
    slice_specs = [
        s for s in spectra
        if s.meta["stage_label"] == "stage1" and s.meta["snr_label"] == 50
    ]
    assert slice_specs, "expected a non-empty stage1/snr50 slice"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = grid.run_grid(slice_specs, n_boot=0)
    df = df.merge(truth, on="case_id", how="left")
    matched = np.where(
        df["intensity"] == "area",
        df["true_id_ig_area"], df["true_id_ig_height"],
    )
    df["true_id_ig"] = matched.astype(float)
    df["error"] = df["id_ig"] - df["true_id_ig"]

    class_bias = (
        df.groupby(["lineshape", "baseline", "peak_set", "intensity"])["error"]
        .mean()
        .abs()
    )
    best = class_bias.min()
    assert np.isfinite(best)
    assert best < V3_BIAS_TOL, (
        f"no class cleared V3: best mean |bias| = {best:.4f} "
        f">= {V3_BIAS_TOL}"
    )


# --------------------------------------------------------------------------- #
# Schema freeze: downstream modules reference only RESULT_COLUMNS (+ declared
# derived columns).  grid.RESULT_COLUMNS is the single source of truth.
# --------------------------------------------------------------------------- #
def _string_column_literals(path):
    """Column-name string literals used as subscripts or in column-arg calls."""
    with open(path) as fh:
        tree = ast.parse(fh.read())
    cols = set()

    def str_consts(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value
        elif isinstance(node, (ast.List, ast.Tuple)):
            for elt in node.elts:
                yield from str_consts(elt)

    column_calls = {
        "groupby", "sort_values", "set_index", "merge", "drop", "pivot",
        "value_counts", "rename", "reset_index",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                cols.add(sl.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in column_calls:
                for arg in node.args:
                    cols.update(str_consts(arg))
                for kw in node.keywords:
                    cols.update(str_consts(kw.value))
    return cols


def test_schema_freeze_downstream_uses_only_result_columns():
    allowed = (
        set(RESULT_COLUMNS)
        | set(robust.OUTPUT_COLUMNS)
        | {robust.RANK_COLUMN}
    )
    src_dir = os.path.dirname(grid.__file__)
    # robust.py must be present and clean; selectors/viz are scanned when they
    # exist (skipped cleanly while still stubs).  RESULT_COLUMNS is the single
    # source of truth for input schema.
    robust_cols = _string_column_literals(os.path.join(src_dir, "robust.py"))
    assert robust_cols <= allowed, (
        f"robust.py references non-schema columns: {robust_cols - allowed}"
    )

    for name in ("selectors.py", "viz.py"):
        path = os.path.join(src_dir, name)
        if not os.path.exists(path):
            continue
        cols = _string_column_literals(path)
        assert cols <= allowed, (
            f"{name} references non-schema columns: {cols - allowed}"
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _result_row(case_id, instance, baseline, lineshape, bwf, peak_set,
                intensity, id_ig, true, covered=True):
    row = {c: np.nan for c in RESULT_COLUMNS}
    # Covered: a wide interval bracketing the truth.  Not covered: an interval
    # placed well above the truth so it genuinely excludes it.
    lo95, hi95 = (true - 1.0, true + 1.0) if covered else (true + 10.0, true + 11.0)
    err = (id_ig - true) if np.isfinite(id_ig) else np.nan
    row.update(
        {
            "case_id": f"{case_id}_{instance}",
            "stage_label": "stage1",
            "snr_label": 50,
            "severity": "none",
            "instance": instance,
            "material_class": "M",
            "baseline": baseline,
            "lineshape": lineshape,
            "bwf_g": bwf,
            "peak_set": peak_set,
            "intensity": intensity,
            "id_ig": id_ig,
            "lo95": lo95,
            "hi95": hi95,
            "sigma_stat": 0.1,
            "n_failed": 0,
            "redchi": 1.0,
            "aic": 0.0,
            "bic": 0.0,
            "la": np.nan,
            "n_d": np.nan,
            "true_id_ig": true,
            "error": err,
            "abs_error": abs(err) if np.isfinite(err) else np.nan,
        }
    )
    return row


def _toy_results():
    rows = []
    for i in range(4):
        rows.append(_result_row("A", i, "als", "lorentzian", False, "DG",
                                 "area", 1.01, 1.0))
        rows.append(_result_row("B", i, "poly3", "gaussian", False, "DGDp",
                                 "height", 1.20, 1.0))
    return pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
