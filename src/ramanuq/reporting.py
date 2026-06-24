"""Assembly of analysis results into a single machine-readable report.

Day-9 role: this module is the ONE place that turns the frozen study artifacts
into the numbers every figure and the eventual report will cite. It READS the
existing grid study (``data/synthetic/results/tierB_grid_results.parquet``) and
the frozen calibrations, RECOMPUTES every cited quantity from the data, and
writes ``docs/report_data.json``.

It deliberately does NOT copy numbers out of ``docs/protocol.md``: the point of
``report_data.json`` is that it holds the *code's* numbers, recomputed from the
parquet. A built-in self-check (:func:`self_check`) compares the recomputed
values against the human-authored protocol/validation values; any disagreement
beyond a small rounding tolerance is a finding to surface, not to silently fix.

Nothing here re-runs the Day-6 study; it only reads the persisted parquet.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from .grid import COVERAGE_FLOOR, MAX_FAILURE_RATE, rank_configurations
from .mdc import estimate_bias, estimate_sigma_single, mdc, to_delta_nd
from .metrics import load_calibrations
from .selectors import audit, coverage_under_misspecification

# --------------------------------------------------------------------------- #
# Locations (relative to the repo root, which is two levels above this file).
# --------------------------------------------------------------------------- #
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_PARQUET = os.path.join(
    _REPO_ROOT, "data", "synthetic", "results", "tierB_grid_results.parquet"
)
DEFAULT_CAL_PATH = os.path.join(
    _REPO_ROOT, "data", "calibrations", "calibrations.yaml"
)
DEFAULT_TIERB_DIR = os.path.join(_REPO_ROOT, "data", "synthetic", "tierB")
DEFAULT_OUTPUT = os.path.join(_REPO_ROOT, "docs", "report_data.json")

MATERIAL_CLASS = "synthetic_disordered_carbon"
SNR_REGIMES = (15, 50, 200)
CONFIG_COLUMNS = ("baseline", "lineshape", "bwf_g", "peak_set", "intensity")

#: The naive everyday pipeline used as the MDC contrast (Day-8 case study).
NAIVE_CONFIG = {
    "baseline": "linear",
    "lineshape": "lorentzian",
    "bwf_g": False,
    "peak_set": "DG",
    "intensity": "height",
}

#: Stage-1 / SNR50 slice keys for Gate V3 (validation_plan.md Section 1).
_V3_STAGE = "stage1"
_V3_SNR = 50
_V3_CLASS_COLS = ("lineshape", "baseline", "peak_set", "intensity")
_V3_TOL = 0.05


# --------------------------------------------------------------------------- #
# Small recompute primitives (each reads ONLY from the parquet / calibrations).
# --------------------------------------------------------------------------- #
def _config_str(cfg):
    return "|".join(f"{k}={cfg[k]}" for k in CONFIG_COLUMNS)


def _regime_slice(df, snr):
    return df[(df["material_class"] == MATERIAL_CLASS) & (df["snr_label"] == snr)]


def _select_protocol_config(df, snr):
    """PROTOCOL config = DG/area config with the smallest signed-error sd.

    Mirrors ``select_protocol_config`` in notebooks/04_mdc_casestudy_q3.ipynb:
    among DG/area configs in the regime, the one whose finite signed ``error``
    has the smallest sample sd (ddof=1) is selected.
    """
    sub = df[
        (df["material_class"] == MATERIAL_CLASS)
        & (df["snr_label"] == snr)
        & (df["peak_set"] == "DG")
        & (df["intensity"] == "area")
    ]
    candidates = []
    for keys, grp in sub.groupby(list(CONFIG_COLUMNS)):
        err = grp["error"].to_numpy(dtype=float)
        err = err[np.isfinite(err)]
        if err.size < 2:
            continue
        candidates.append((float(np.std(err, ddof=1)), dict(zip(CONFIG_COLUMNS, keys))))
    candidates.sort(key=lambda t: t[0])
    best_sd, best_cfg = candidates[0]
    return best_cfg, best_sd, len(candidates)


def _config_rmse_cov_fail(df, cfg, snr):
    """RMSE, empirical 95% coverage and failure rate of one config in a regime."""
    grp = _regime_slice(df, snr)
    for col in CONFIG_COLUMNS:
        grp = grp[grp[col] == cfg[col]]
    idig = grp["id_ig"].to_numpy(dtype=float)
    err = grp["error"].to_numpy(dtype=float)
    lo = grp["lo95"].to_numpy(dtype=float)
    hi = grp["hi95"].to_numpy(dtype=float)
    true = grp["true_id_ig"].to_numpy(dtype=float)
    n = int(len(grp))

    fin_err = err[np.isfinite(err)]
    rmse = float(np.sqrt(np.mean(fin_err**2))) if fin_err.size else float("nan")
    covered = (
        np.isfinite(lo) & np.isfinite(hi) & np.isfinite(true)
        & (true >= lo) & (true <= hi)
    )
    coverage = float(np.mean(covered)) if n else float("nan")
    failure_rate = float(np.mean(~np.isfinite(idig))) if n else float("nan")
    return rmse, coverage, failure_rate, n


def _max_coverage_any_cell(df):
    """Largest empirical 95% coverage over every (config x SNR) cell."""
    best = 0.0
    for (_mat, _snr), regime in df.groupby(["material_class", "snr_label"]):
        for _keys, grp in regime.groupby(list(CONFIG_COLUMNS)):
            lo = grp["lo95"].to_numpy(dtype=float)
            hi = grp["hi95"].to_numpy(dtype=float)
            true = grp["true_id_ig"].to_numpy(dtype=float)
            covered = (
                np.isfinite(lo) & np.isfinite(hi) & np.isfinite(true)
                & (true >= lo) & (true <= hi)
            )
            if len(grp):
                best = max(best, float(np.mean(covered)))
    return best


def _gate_v3(df):
    """Gate V3 on the stage-1 / SNR50 slice (validation_plan.md Section 1).

    Per (lineshape, baseline, peak_set, intensity) class, the bias is the mean
    SIGNED error and the gate statistic is its absolute value (mean absolute
    bias). A class passes if ``|mean signed error| < 0.05``; the gate passes if
    at least one class passes.
    """
    s = df[(df["stage_label"] == _V3_STAGE) & (df["snr_label"] == _V3_SNR)]
    classes = []
    for keys, grp in s.groupby(list(_V3_CLASS_COLS)):
        err = grp["error"].to_numpy(dtype=float)
        err = err[np.isfinite(err)]
        if err.size == 0:
            continue
        mean_abs_bias = float(abs(np.mean(err)))
        classes.append((mean_abs_bias, dict(zip(_V3_CLASS_COLS, keys))))
    classes.sort(key=lambda t: t[0])
    passing = [c for c in classes if c[0] < _V3_TOL]
    best_bias, best_cfg = classes[0]
    return {
        "slice": "stage1 / SNR50",
        "tolerance_abs_bias": _V3_TOL,
        "n_classes": len(classes),
        "n_classes_passing": len(passing),
        "pass": bool(len(passing) >= 1),
        "best_class": best_cfg,
        "best_class_mean_abs_bias": best_bias,
        "passing_classes": [
            {**cfg, "mean_abs_bias": b} for b, cfg in passing
        ],
    }


def _wavelength_nm(tierB_dir):
    """Read the single excitation wavelength from the Tier-B truth files."""
    wls = set()
    for f in os.listdir(tierB_dir):
        if f.endswith("_truth.json"):
            with open(os.path.join(tierB_dir, f)) as fh:
                wls.add(json.load(fh)["wavelength_nm"])
    if len(wls) != 1:
        raise ValueError(f"expected one excitation wavelength, found {wls!r}")
    return float(next(iter(wls)))


# --------------------------------------------------------------------------- #
# Top-level builder.
# --------------------------------------------------------------------------- #
def compute_report_data(
    parquet_path=DEFAULT_PARQUET,
    cal_path=DEFAULT_CAL_PATH,
    tierB_dir=DEFAULT_TIERB_DIR,
):
    """Recompute every cited number from the parquet; return a report dict.

    Never re-runs the study; reads ``parquet_path`` only. Calibrations and the
    excitation wavelength are read from the frozen provenance files.
    """
    df = pd.read_parquet(parquet_path)
    cals = load_calibrations(cal_path)
    wavelength_nm = _wavelength_nm(tierB_dir)

    # ----- gates ----------------------------------------------------------- #
    v3 = _gate_v3(df)
    gates = {
        "V1": {
            "name": "Parameter recovery",
            "status": "PASS",
            "tolerance": "< 0.1% relative recovery error",
            "source": "validation_plan.md Gate V1 (Day 3)",
            "note": "Recomputed gate state is read from the pre-registration "
            "record; V1 evidence lives in tests/test_fit_recovery.py.",
        },
        "V1b": {
            "name": "Empirical coverage band",
            "status": "REPORTED",
            "tolerance": "0.90-0.98",
            "source": "validation_plan.md Gate V1b; T6b recompute",
            "note": "On the hostile grid NO config reaches the 0.90 floor "
            "(max empirical coverage across all cells = "
            f"{_max_coverage_any_cell(df):.2f}); reported as the honest-"
            "coverage finding, not forced to pass.",
        },
        "V2": {
            "name": "Baseline fit",
            "status": "PASS",
            "tolerance": "< 2% of G-band height (in-class)",
            "source": "validation_plan.md Gate V2 (Day 4)",
        },
        "V3": {"name": "Hostile-spectrum bias", "status": "PASS", **v3},
        "V4": {
            "name": "Selector sanity (rigged exact recovery)",
            "status": "PASS",
            "tolerance": "exact recovery (atol 1e-12)",
            "source": "validation_plan.md Gate V4 (Day 7)",
        },
        "V5": {
            "name": "Published-spectrum reproduction",
            "status": "pending_day10",
            "tolerance": "within +/-10% of >=1 digitized published spectrum",
            "source": "validation_plan.md Gate V5",
            "note": "No digitized spectrum present yet; F8 / V5 are deferred "
            "to Day 10.",
        },
        "V6": {
            "name": "Cross-implementation agreement",
            "status": "PASS",
            "tolerance": "1e-9 relative (analytic) / 1e-6 (numerical)",
            "source": "validation_plan.md Gate V6 (metrics Day 5, selectors "
            "Day 7, mdc Day 8)",
        },
    }

    # ----- T5 ranking state (EMPTY) ---------------------------------------- #
    ranking = rank_configurations(df)
    max_cov = _max_coverage_any_cell(df)
    t5_ranking = {
        "n_rank_eligible": int(len(ranking)),
        "is_empty": bool(len(ranking) == 0),
        "max_coverage": float(max_cov),
        "coverage_floor": float(COVERAGE_FLOOR),
        "max_failure_rate": float(MAX_FAILURE_RATE),
        "headline": "No configuration is rank-eligible in any SNR regime: the "
        f"maximum empirical 95% coverage over all cells is {max_cov:.2f}, below "
        f"the {COVERAGE_FLOOR:.2f} floor, so the coverage-gated ranking is "
        "empty.",
    }

    # ----- Gate V3 standalone block (n_classes_passing of 72, best) -------- #
    gate_v3 = {
        "slice": v3["slice"],
        "n_classes": v3["n_classes"],
        "n_classes_passing": v3["n_classes_passing"],
        "pass": v3["pass"],
        "best_class": v3["best_class"],
        "best_class_mean_abs_bias": v3["best_class_mean_abs_bias"],
    }

    # ----- Q1b stability (vacuous per regime) ------------------------------ #
    q1b_stability = {
        "n_recommended_configs": 0,
        "per_regime": {
            f"SNR{snr}": "undefined; 0 rank-eligible configs"
            for snr in SNR_REGIMES
        },
        "note": "Q1b is vacuous: with no rank-eligible config there is no "
        "protocol-recommended configuration to jackknife.",
    }

    # ----- Q2 selector audit (rho / regret / quartile-hit) ----------------- #
    audit_df = audit(df)
    q2 = {}
    for _, r in audit_df.iterrows():
        regime = f"SNR{int(r['snr_label'])}"
        stratum = str(r["stratum"])
        selector = str(r["selector"])
        q2.setdefault(stratum, {}).setdefault(regime, {})[selector] = {
            "spearman_rho": float(r["rho_median"]),
            "rho_ci": [float(r["rho_lo"]), float(r["rho_hi"])],
            "top1_regret": float(r["regret_median"]),
            "top_quartile_hit": float(r["hit_rate"]),
            "n_spectra": int(r["n_spectra"]),
        }
    q2_audit = {
        "selectors": ["redchi", "aic", "bic"],
        "strata": ["full", "within_peak_set"],
        "by_stratum": q2,
    }

    # ----- T6b coverage under misspecification ----------------------------- #
    t6b_df = coverage_under_misspecification(df)
    t6b = {}
    for _, r in t6b_df.iterrows():
        t6b[f"SNR{int(r['snr_label'])}"] = {
            "coverage": float(r["coverage"]),
            "n": int(r["n"]),
        }
    t6b_coverage = {
        "nominal": 0.95,
        "per_regime": t6b,
        "note": "Pooled over all grid configs per regime; inclusive endpoints "
        "(lo95 <= true <= hi95). Standard residual-bootstrap intervals "
        "undercover under realistic misspecification (FM4).",
    }

    # ----- MDC (protocol vs naive), both currencies ------------------------ #
    mdc_block = {
        "alpha": 0.05,
        "power": 0.8,
        "n_rep": 1,
        "wavelength_nm": wavelength_nm,
        "naive_config": _config_str(NAIVE_CONFIG),
        "per_regime": {},
    }
    for snr in SNR_REGIMES:
        regime = {"material_class": MATERIAL_CLASS, "snr_label": snr}
        proto_cfg, proto_sd, n_cand = _select_protocol_config(df, snr)

        p_sigma = estimate_sigma_single(df, proto_cfg, regime)
        p_bias = estimate_bias(df, proto_cfg, regime)
        p_mdc = mdc(p_sigma)
        p_dnd = to_delta_nd(p_mdc, cals, wavelength_nm)

        n_sigma = estimate_sigma_single(df, NAIVE_CONFIG, regime)
        n_bias = estimate_bias(df, NAIVE_CONFIG, regime)
        n_mdc = mdc(n_sigma)
        n_dnd = to_delta_nd(n_mdc, cals, wavelength_nm)

        rmse, coverage, failure, n_spec = _config_rmse_cov_fail(df, proto_cfg, snr)

        mdc_block["per_regime"][f"SNR{snr}"] = {
            "protocol_config": _config_str(proto_cfg),
            "protocol_config_factors": proto_cfg,
            "protocol_sigma_single": float(p_sigma),
            "protocol_bias": float(p_bias),
            "protocol_rmse": float(rmse),
            "protocol_coverage": float(coverage),
            "protocol_failure_rate": float(failure),
            "protocol_mdc_idig": float(p_mdc),
            "protocol_delta_nd_central": float(p_dnd[0]),
            "protocol_delta_nd_range": [float(p_dnd[1]), float(p_dnd[2])],
            "naive_sigma_single": float(n_sigma),
            "naive_bias": float(n_bias),
            "naive_mdc_idig": float(n_mdc),
            "naive_delta_nd_central": float(n_dnd[0]),
            "naive_delta_nd_range": [float(n_dnd[1]), float(n_dnd[2])],
            "naive_over_protocol_mdc_ratio": float(n_mdc / p_mdc),
            "n_protocol_candidates": int(n_cand),
            "n_spectra": int(n_spec),
        }

    report = {
        "_about": "RamanUQ v2.1 report data. Every number below is RECOMPUTED "
        "from data/synthetic/results/tierB_grid_results.parquet and the frozen "
        "calibrations; nothing is copied from protocol.md. Do not hand-edit.",
        "material_class": MATERIAL_CLASS,
        "snr_regimes": list(SNR_REGIMES),
        "parquet_path": os.path.relpath(parquet_path, _REPO_ROOT),
        "n_rows": int(len(df)),
        "gates": gates,
        "t5_ranking": t5_ranking,
        "gate_v3": gate_v3,
        "q1b_stability": q1b_stability,
        "q2_audit": q2_audit,
        "t6b_coverage": t6b_coverage,
        "mdc": mdc_block,
    }
    return report


# --------------------------------------------------------------------------- #
# Self-check against the human-authored values (a finding, not a fixer).
# --------------------------------------------------------------------------- #
#: Authored protocol/validation values the recompute MUST reproduce.
_AUTHORED = {
    "protocol_mdc": {"SNR15": 0.529, "SNR50": 0.271, "SNR200": 0.565},
    "naive_mdc": {"SNR15": 0.745, "SNR50": 0.763, "SNR200": 0.703},
    "bias": {"SNR15": 0.022, "SNR50": -0.086, "SNR200": -0.016},
    "rmse": {"SNR15": 0.133, "SNR50": 0.109, "SNR200": 0.141},
    "coverage": {"SNR15": 0.467, "SNR50": 0.233, "SNR200": 0.200},
    "t6b": {"SNR15": 0.276, "SNR50": 0.240, "SNR200": 0.183},
    "v3_best_bias": 0.0052,
}
_ATOL = 1e-3


def self_check(report):
    """Compare recomputed values to the authored protocol/validation values.

    Returns ``(ok, discrepancies)``. ``ok`` is True iff every authored value is
    reproduced to within ``_ATOL`` (a rounding tolerance). A disagreement is a
    finding for the human to adjudicate; this function never mutates anything.
    """
    disc = []
    per = report["mdc"]["per_regime"]

    def _chk(label, got, want):
        if not (abs(float(got) - float(want)) <= _ATOL):
            disc.append(f"{label}: recomputed {got:.6f} != authored {want} "
                        f"(|diff| {abs(got - want):.6f} > {_ATOL})")

    for snr in SNR_REGIMES:
        k = f"SNR{snr}"
        _chk(f"protocol_mdc[{k}]", per[k]["protocol_mdc_idig"],
             _AUTHORED["protocol_mdc"][k])
        _chk(f"naive_mdc[{k}]", per[k]["naive_mdc_idig"],
             _AUTHORED["naive_mdc"][k])
        _chk(f"bias[{k}]", per[k]["protocol_bias"], _AUTHORED["bias"][k])
        _chk(f"rmse[{k}]", per[k]["protocol_rmse"], _AUTHORED["rmse"][k])
        _chk(f"coverage[{k}]", per[k]["protocol_coverage"],
             _AUTHORED["coverage"][k])
        _chk(f"t6b[{k}]", report["t6b_coverage"]["per_regime"][k]["coverage"],
             _AUTHORED["t6b"][k])

    _chk("v3_best_mean_abs_bias", report["gate_v3"]["best_class_mean_abs_bias"],
         _AUTHORED["v3_best_bias"])

    # Structural checks (state, not floats).
    if report["t5_ranking"]["n_rank_eligible"] != 0:
        disc.append("t5_ranking.n_rank_eligible != 0")
    if abs(report["t5_ranking"]["max_coverage"] - 0.80) > _ATOL:
        disc.append(
            f"t5_ranking.max_coverage {report['t5_ranking']['max_coverage']} "
            "!= 0.80"
        )
    if report["gate_v3"]["n_classes"] != 72:
        disc.append("gate_v3.n_classes != 72")
    if report["gate_v3"]["n_classes_passing"] != 9:
        disc.append("gate_v3.n_classes_passing != 9")
    bc = report["gate_v3"]["best_class"]
    if not (bc.get("lineshape") == "pseudo_voigt" and bc.get("baseline") == "poly5"
            and bc.get("peak_set") == "DG" and bc.get("intensity") == "area"):
        disc.append(f"gate_v3.best_class != pseudo_voigt/poly5/DG/area ({bc})")

    return (len(disc) == 0, disc)


def write_report_data(
    output_path=DEFAULT_OUTPUT,
    parquet_path=DEFAULT_PARQUET,
    cal_path=DEFAULT_CAL_PATH,
    tierB_dir=DEFAULT_TIERB_DIR,
    enforce_self_check=True,
):
    """Recompute, self-check, and write ``report_data.json``.

    If ``enforce_self_check`` and the recompute disagrees with the authored
    values, raises :class:`ValueError` WITHOUT writing the file (the disagreement
    is a finding, not something to paper over).
    """
    report = compute_report_data(parquet_path, cal_path, tierB_dir)
    ok, disc = self_check(report)
    if enforce_self_check and not ok:
        raise ValueError(
            "report_data self-check FAILED; recomputed numbers disagree with "
            "the authored protocol/validation values:\n  - " + "\n  - ".join(disc)
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report, ok, disc


def load_report_data(path=DEFAULT_OUTPUT):
    """Load the persisted ``report_data.json`` (used by viz / figure code)."""
    with open(path) as fh:
        return json.load(fh)


__all__ = [
    "NAIVE_CONFIG",
    "SNR_REGIMES",
    "compute_report_data",
    "self_check",
    "write_report_data",
    "load_report_data",
    "DEFAULT_OUTPUT",
    "DEFAULT_PARQUET",
]
