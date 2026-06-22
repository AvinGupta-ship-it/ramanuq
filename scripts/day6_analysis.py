"""Day-6 analysis: generate ranking / decomposition / Q1b outputs from the
ALREADY-RUN Tier-B grid study.  Does NOT re-run the study; loads the existing
parquet and calls the already-implemented grid/robust functions.

Faithful finding: under the pre-registered 0.90 coverage floor (== V1b lower
bound), NO configuration is rank-eligible in any SNR regime, because the
bootstrap (statistical-only) intervals systematically undercover on the hostile
Tier-B spectra (max empirical coverage = 0.80 < 0.90).  The Q1 ranking (T5) and
the Q1b jackknife (T9) are therefore EMPTY.  This module reports that outcome
faithfully and additionally records the descriptive RMSE-ordering (clearly
labelled NOT rank-eligible) and Gate V3, which are independent of coverage.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from ramanuq import grid, robust

RESULTS_DIR = os.path.join("data", "synthetic", "results")
PARQUET = os.path.join(RESULTS_DIR, "tierB_grid_results.parquet")

COVERAGE_FLOOR = 0.90
MAX_FAIL = 0.05
CFG_COLS = ["baseline", "lineshape", "bwf_g", "peak_set", "intensity"]


def _native(v):
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    return v


def _jsonify(obj):
    if isinstance(obj, dict):
        return {str(_native(k)): _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return _native(obj)


def _full_cell_table(df):
    """Per (regime, config) cell: rmse, coverage, failure_rate, eligibility.

    This mirrors grid.rank_configurations' internal accounting but keeps ALL
    cells (eligible and not) so we can describe the RMSE ordering and show why
    nothing is rank-eligible.  It does NOT change the ranking rule.
    """
    rows = []
    for (mat, snr), regime in df.groupby(["material_class", "snr_label"]):
        for keys, grp in regime.groupby(CFG_COLS):
            idig = grp["id_ig"].to_numpy(dtype=float)
            lo = grp["lo95"].to_numpy(dtype=float)
            hi = grp["hi95"].to_numpy(dtype=float)
            true = grp["true_id_ig"].to_numpy(dtype=float)
            err = grp["error"].to_numpy(dtype=float)
            n = len(grp)
            fr = float(np.mean(~np.isfinite(idig))) if n else 1.0
            cov = float(
                np.mean(
                    np.isfinite(lo) & np.isfinite(hi) & np.isfinite(true)
                    & (true >= lo) & (true <= hi)
                )
            ) if n else 0.0
            fin = err[np.isfinite(err)]
            rmse = float(np.sqrt(np.mean(fin**2))) if fin.size else float("nan")
            r = dict(zip(CFG_COLS, keys))
            r.update(
                material_class=mat, snr_label=int(snr), n_spectra=n,
                rmse=rmse, coverage=cov, failure_rate=fr,
                eligible=(cov >= COVERAGE_FLOOR) and (fr <= MAX_FAIL),
            )
            rows.append(r)
    return pd.DataFrame(rows)


def main():
    df = pd.read_parquet(PARQUET)

    # ---- Q1 ranking (T5) and Q1b jackknife (T9), called exactly as specified.
    t5 = grid.rank_configurations(df, coverage_floor=COVERAGE_FLOOR, max_fail=MAX_FAIL)
    dec = grid.decompose(df)
    t9 = robust.jackknife_ranking(df, coverage_floor=COVERAGE_FLOOR, max_fail=MAX_FAIL)

    # ---- Descriptive full-cell accounting (eligible + not) ----------------
    cells = _full_cell_table(df)
    cells.to_csv(os.path.join(RESULTS_DIR, "config_cell_accounting.csv"), index=False)

    # RMSE-order leaders per regime (NOT rank-eligible; descriptive only).
    rmse_leaders = {}
    for snr, grp in cells.groupby("snr_label"):
        g = grp[np.isfinite(grp["rmse"])].sort_values("rmse").head(3)
        rmse_leaders[int(snr)] = [
            {
                **{c: _native(r[c]) for c in CFG_COLS},
                "rmse": float(r["rmse"]),
                "coverage": float(r["coverage"]),
                "failure_rate": float(r["failure_rate"]),
                "eligible": bool(r["eligible"]),
            }
            for _, r in g.iterrows()
        ]

    # ---- Write T5 / T9 fragments (empty -> headers preserved) --------------
    t5_path = os.path.join(RESULTS_DIR, "t5_ranking.csv")
    t9_path = os.path.join(RESULTS_DIR, "t9_stability.csv")
    if t5.empty and len(t5.columns) == 0:
        t5 = pd.DataFrame(columns=CFG_COLS + [
            "material_class", "snr_label", "n_spectra", "rmse",
            "coverage", "failure_rate", "eligible", "rank"])
    t5.to_csv(t5_path, index=False)
    if t9.empty:
        t9 = pd.DataFrame(columns=CFG_COLS + [
            "material_class", "snr_label", "top_quartile_retention",
            "rank_iqr", "flip_flag", "n_resamples"])
    t9.to_csv(t9_path, index=False)

    # ==================================================================== #
    # Task 3(a): spread (sigma_meth / RMSE) by baseline severity
    # ==================================================================== #
    severity_spread = {}
    for sev in ["none", "mild", "strong"]:
        err = df[df["severity"] == sev]["error"].to_numpy(dtype=float)
        err = err[np.isfinite(err)]
        sigma = float(np.std(err)) if err.size else float("nan")
        rmse = float(np.sqrt(np.mean(err**2))) if err.size else float("nan")
        severity_spread[sev] = {
            "sigma_meth": sigma,
            "rmse": rmse,
            "sigma_over_rmse": (sigma / rmse if rmse else float("nan")),
            "n_valid": int(err.size),
        }

    # ==================================================================== #
    # Task 3(b): failure rates by peak_set
    # ==================================================================== #
    failure_by_peakset = {}
    for ps in ["DG", "DGDp", "DGDpD3D4"]:
        sub = df[df["peak_set"] == ps]
        n = len(sub)
        failed = int((~np.isfinite(sub["id_ig"].to_numpy(dtype=float))).sum())
        failure_by_peakset[ps] = {
            "n_rows": int(n),
            "n_failed": failed,
            "failure_rate": failed / n if n else float("nan"),
            "contains_Dprime": ps in ("DGDp", "DGDpD3D4"),
        }

    # ==================================================================== #
    # Task 4: Gate V3 re-confirmation (independent of coverage)
    #   stage1 / SNR50 slice, mean |mean-error| per
    #   (lineshape, baseline, peak_set, intensity) class.
    # ==================================================================== #
    v3_slice = df[(df["stage_label"] == "stage1") & (df["snr_label"] == 50)]
    v3_rows = []
    for keys, grp in v3_slice.groupby(["lineshape", "baseline", "peak_set", "intensity"]):
        err = grp["error"].to_numpy(dtype=float)
        err = err[np.isfinite(err)]
        mean_bias = float(abs(np.mean(err))) if err.size else float("nan")
        v3_rows.append({
            "lineshape": keys[0], "baseline": keys[1],
            "peak_set": keys[2], "intensity": keys[3],
            "n_valid": int(err.size), "mean_abs_bias": mean_bias,
            "below_5pct": bool(np.isfinite(mean_bias) and mean_bias < 0.05),
        })
    v3_df = pd.DataFrame(v3_rows).sort_values("mean_abs_bias").reset_index(drop=True)
    v3_pass_classes = v3_df[v3_df["below_5pct"]]
    v3_pass = bool(len(v3_pass_classes) >= 1)
    v3_df.to_csv(os.path.join(RESULTS_DIR, "v3_classes.csv"), index=False)

    # ==================================================================== #
    # Spot-recompute offer: best-by-RMSE config (NOT rank-eligible), valid row
    # ==================================================================== #
    best = cells[np.isfinite(cells["rmse"])].sort_values("rmse").iloc[0]
    mask = np.ones(len(df), dtype=bool)
    for c in CFG_COLS:
        mask &= df[c] == best[c]
    cand = df[mask & np.isfinite(df["error"]) & (df["snr_label"] == best["snr_label"])]
    row = cand.sort_values("abs_error").iloc[0]
    spot = {
        "config": {c: _native(best[c]) for c in CFG_COLS},
        "config_note": "best-by-RMSE in its regime; NOT rank-eligible "
                       f"(coverage {float(best['coverage']):.3f} < 0.90 floor)",
        "regime_snr_label": int(best["snr_label"]),
        "case_id": str(row["case_id"]),
        "stage_label": str(row["stage_label"]),
        "snr_label": int(row["snr_label"]),
        "severity": str(row["severity"]),
        "instance": int(row["instance"]),
        "id_ig": float(row["id_ig"]),
        "true_id_ig": float(row["true_id_ig"]),
        "error": float(row["error"]),
        "abs_error": float(row["abs_error"]),
    }

    # ==================================================================== #
    # report_data fragment
    # ==================================================================== #
    report_data = {
        "n_rows": int(len(df)),
        "n_valid_error": int(df["error"].notna().sum()),
        "ranking_eligible_count": int(len(t5.dropna(subset=["rank"]))
                                      if "rank" in t5 and not t5.empty else 0),
        "ranking_is_empty": bool(t5.empty or t5["rank"].notna().sum() == 0
                                 if "rank" in t5 else True),
        "max_empirical_coverage": float(cells["coverage"].max()),
        "coverage_floor": COVERAGE_FLOOR,
        "headline": (
            "No configuration is rank-eligible: max empirical 95% coverage "
            f"{float(cells['coverage'].max()):.2f} < {COVERAGE_FLOOR} floor in "
            "every SNR regime. T5 and T9 are empty. Bootstrap statistical "
            "intervals undercover on hostile spectra."
        ),
        "rmse_order_leaders_per_snr_NOT_eligible": rmse_leaders,
        "descriptive_decomposition": {
            "label": dec["label"],
            "sigma_meth": dec["sigma_meth"],
            "id_ig_sd": dec["id_ig_sd"],
            "range": list(dec["range"]),
            "per_factor": _jsonify(dec["per_factor"]),
        },
        "q1b_stability": {
            "n_recommended_configs": 0,
            "note": "Q1b is vacuous: with no rank-eligible config there is no "
                    "protocol-recommended configuration to jackknife. T9 empty.",
        },
        "gate_v3": {
            "slice": "stage1 / SNR50",
            "n_classes": int(len(v3_df)),
            "n_classes_below_5pct": int(len(v3_pass_classes)),
            "pass": v3_pass,
            "best_class_mean_abs_bias": float(v3_df["mean_abs_bias"].min()),
            "classes_below_5pct": [
                {**{k: _native(r[k]) for k in
                    ["lineshape", "baseline", "peak_set", "intensity"]},
                 "mean_abs_bias": float(r["mean_abs_bias"])}
                for _, r in v3_pass_classes.iterrows()
            ],
        },
        "severity_spread": severity_spread,
        "failure_rate_by_peakset": failure_by_peakset,
        "spot_recompute_offer": spot,
    }
    rd_path = os.path.join(RESULTS_DIR, "day6_report_data.json")
    with open(rd_path, "w") as fh:
        json.dump(_jsonify(report_data), fh, indent=2)

    return {
        "df": df, "t5": t5, "t9": t9, "dec": dec, "cells": cells,
        "rmse_leaders": rmse_leaders, "v3_df": v3_df,
        "v3_pass_classes": v3_pass_classes, "v3_pass": v3_pass,
        "severity_spread": severity_spread,
        "failure_by_peakset": failure_by_peakset, "spot": spot,
        "report_data": report_data,
        "paths": {
            "t5": t5_path, "t9": t9_path, "report_data": rd_path,
            "v3": os.path.join(RESULTS_DIR, "v3_classes.csv"),
            "cells": os.path.join(RESULTS_DIR, "config_cell_accounting.csv"),
        },
    }


if __name__ == "__main__":
    res = main()
    rd = res["report_data"]
    print("=== Day-6 analysis ===")
    print(rd["headline"])
    print("\nFiles written:")
    for k, p in res["paths"].items():
        print(f"  {k}: {p}")
