"""Configuration-grid study over the hostile (Tier-B) suite.

This module runs a factorial grid of pipeline configurations against the
hostile spectra, joins each fit to its operational ground truth, and produces
the Q1 ranking and a DESCRIPTIVE (non-causal) spread decomposition.

Pre-registered references (docs/validation_plan.md):

- **Q1 ranking rule (Section 3):** within each (material class, SNR regime),
  order configurations by RMSE of I_D/I_G error against truth, ascending. A
  configuration is rank-eligible only if its empirical 95% coverage is
  >= 0.90 (the V1b lower bound) AND its failure rate is <= 0.05. Ineligible
  configurations are EXCLUDED from the ranking, not ranked last. RMSE is the
  ordering metric; coverage and failure are eligibility gates.
- **Gate V3 (Section 1):** at least one configuration class must achieve mean
  absolute bias below 5% on stage-1 hostile spectra at SNR 50.

The single source of truth for the result schema is :data:`RESULT_COLUMNS`.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from .fit import PipelineConfig, fit_spectrum
from .io import load_spectrum
from .metrics import compute_metrics, load_calibrations

# --------------------------------------------------------------------------- #
# Pre-registered constants (read from docs/validation_plan.md Section 3).
# These are NOT invented here; they reference the frozen plan.
# --------------------------------------------------------------------------- #
#: Rank-eligibility coverage floor (validation_plan.md Section 3; == V1b lower
#: bound 0.90 of the pre-registered coverage band 0.90-0.98).
COVERAGE_FLOOR = 0.90
#: Rank-eligibility failure-rate cap (validation_plan.md Section 3).
MAX_FAILURE_RATE = 0.05

# --------------------------------------------------------------------------- #
# Factor levels (the 5 degrees of freedom).
# --------------------------------------------------------------------------- #
BASELINES = ("linear", "poly3", "poly5", "als")
LINESHAPES = ("lorentzian", "gaussian", "pseudo_voigt")
PEAK_SETS = ("DG", "DGDp", "DGDpD3D4")
INTENSITIES = ("height", "area")

#: Default constant material class for the single-material Tier-B suite.
DEFAULT_MATERIAL_CLASS = "synthetic_disordered_carbon"

# --------------------------------------------------------------------------- #
# FROZEN result schema.  Any downstream module (selectors/viz/robust) must
# reference only names in this tuple for input columns.
# --------------------------------------------------------------------------- #
RESULT_COLUMNS = (
    # --- spectrum / truth join keys ---
    "case_id",
    "stage_label",
    "snr_label",
    "severity",
    "instance",
    "material_class",
    # --- configuration factors (the 5 DOF) ---
    "baseline",
    "lineshape",
    "bwf_g",
    "peak_set",
    "intensity",
    # --- fitted metric + interval ---
    "id_ig",
    "lo95",
    "hi95",
    "sigma_stat",
    "n_failed",
    "redchi",
    "aic",
    "bic",
    # --- calibrated quantities (NaN where stage-guarded / undefined) ---
    "la",
    "n_d",
    # --- truth + error (filled by the truth join in run_study) ---
    "true_id_ig",
    "error",
    "abs_error",
)

# Default location of the frozen calibration provenance file.
_DEFAULT_CAL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "calibrations", "calibrations.yaml"
)

# 95% normal-interval z used only to summarise a half-width as sigma_stat.
_Z95 = 1.959963984540054


# --------------------------------------------------------------------------- #
# Grid construction
# --------------------------------------------------------------------------- #
def default_grid():
    """Factorial grid of configuration dicts.

    Factors: baseline x lineshape x bwf_g x peak_set x intensity.  ``bwf_g=True``
    is emitted ONLY with ``lineshape == "lorentzian"`` (a Breit-Wigner-Fano G
    band is only defined on the Lorentzian family); it is never emitted for
    gaussian or pseudo_voigt.
    """
    configs = []
    for baseline in BASELINES:
        for lineshape in LINESHAPES:
            bwf_options = (False, True) if lineshape == "lorentzian" else (False,)
            for bwf_g in bwf_options:
                for peak_set in PEAK_SETS:
                    for intensity in INTENSITIES:
                        configs.append(
                            {
                                "baseline": baseline,
                                "lineshape": lineshape,
                                "bwf_g": bwf_g,
                                "peak_set": peak_set,
                                "intensity": intensity,
                            }
                        )
    return configs


def _to_pipeline_config(cfg):
    """Map a grid config dict to a :class:`PipelineConfig`."""
    return PipelineConfig(
        peak_set=cfg["peak_set"],
        lineshape=cfg["lineshape"],
        bwf_g=cfg["bwf_g"],
        baseline_method=cfg["baseline"],
    )


def _empty_row(cfg, meta):
    """A result row for a fit/metric that could not be produced."""
    row = {c: np.nan for c in RESULT_COLUMNS}
    row.update(
        {
            "case_id": meta.get("case_id"),
            "stage_label": meta.get("stage_label"),
            "snr_label": meta.get("snr_label"),
            "severity": meta.get("severity"),
            "instance": meta.get("instance"),
            "material_class": meta.get("material_class", DEFAULT_MATERIAL_CLASS),
            "baseline": cfg["baseline"],
            "lineshape": cfg["lineshape"],
            "bwf_g": cfg["bwf_g"],
            "peak_set": cfg["peak_set"],
            "intensity": cfg["intensity"],
        }
    )
    return row


# --------------------------------------------------------------------------- #
# Grid execution
# --------------------------------------------------------------------------- #
def run_grid(spectra, configs=None, n_boot=80, seed=0, calibrations=None):
    """Fit every (spectrum, config) pair and return a tidy result frame.

    Each spectrum is a :class:`~ramanuq.io.Spectrum` whose ``meta`` carries the
    join keys (``case_id``, ``stage_label``, ``snr_label``, ``severity``,
    ``instance``, ``material_class``).  For each config, ``fit_spectrum`` runs
    then ``compute_metrics`` is called with the MATCHING intensity definition
    (``intensity == "area"`` -> area; ``"height"`` -> height).

    Never raises on a failed fit: a failure is recorded (NaN metrics, the fit's
    ``n_failed``) and the run continues.  The truth columns (``true_id_ig``,
    ``error``, ``abs_error``) are left NaN here; they are filled by the truth
    join in :func:`run_study`.  Returns a DataFrame whose columns are EXACTLY
    :data:`RESULT_COLUMNS`.
    """
    if configs is None:
        configs = default_grid()
    if calibrations is None:
        calibrations = load_calibrations(_DEFAULT_CAL_PATH)

    rows = []
    for spec in spectra:
        meta = dict(spec.meta)
        for cfg in configs:
            try:
                fit = fit_spectrum(
                    spec, _to_pipeline_config(cfg), n_boot=n_boot, seed=seed
                )
            except Exception:  # pragma: no cover - pipeline never raises
                rows.append(_empty_row(cfg, meta))
                continue

            row = _empty_row(cfg, meta)
            # Statistics always available from the fit (NaN on primary failure).
            row["n_failed"] = fit.n_failed
            row["redchi"] = fit.redchi
            row["aic"] = fit.aic
            row["bic"] = fit.bic

            try:
                metrics = compute_metrics(fit, calibrations, cfg["intensity"])
            except Exception:
                rows.append(row)
                continue

            lo95, hi95 = metrics.id_ig_interval
            row["id_ig"] = float(metrics.id_ig)
            row["lo95"] = float(lo95)
            row["hi95"] = float(hi95)
            if np.isfinite(lo95) and np.isfinite(hi95):
                row["sigma_stat"] = (float(hi95) - float(lo95)) / (2.0 * _Z95)
            row["la"] = (
                float(metrics.la_cancado2006)
                if np.isfinite(metrics.la_cancado2006)
                else np.nan
            )
            row["n_d"] = float(metrics.n_d) if np.isfinite(metrics.n_d) else np.nan
            rows.append(row)

    df = pd.DataFrame(rows, columns=list(RESULT_COLUMNS))
    return df


# --------------------------------------------------------------------------- #
# Tier-B suite loading + study
# --------------------------------------------------------------------------- #
def _load_tierB_suite(tierB_dir):
    """Load Tier-B spectra (with join-key meta) and a truth frame.

    Returns ``(spectra, truth_df)`` where ``truth_df`` is keyed by ``case_id``
    with both ``true_id_ig_area`` and ``true_id_ig_height``.
    """
    spectra = []
    truth_rows = []
    truth_files = sorted(
        f for f in os.listdir(tierB_dir) if f.endswith("_truth.json")
    )
    for tf in truth_files:
        with open(os.path.join(tierB_dir, tf)) as fh:
            truth = json.load(fh)
        case_id = truth["case_id"]
        csv_path = os.path.join(tierB_dir, case_id + ".csv")
        data = pd.read_csv(csv_path)
        spec = load_spectrum(
            data.iloc[:, 0].to_numpy(),
            data.iloc[:, 1].to_numpy(),
            truth["wavelength_nm"],
            meta={
                "case_id": case_id,
                "stage_label": truth["stage_label"],
                "snr_label": int(truth["snr_label"]),
                "severity": truth["severity"],
                "instance": int(truth["instance"]),
                "material_class": DEFAULT_MATERIAL_CLASS,
            },
        )
        spectra.append(spec)
        truth_rows.append(
            {
                "case_id": case_id,
                "true_id_ig_area": float(truth["true_id_ig_area"]),
                "true_id_ig_height": float(truth["true_id_ig_height"]),
            }
        )
    truth_df = pd.DataFrame(truth_rows)
    return spectra, truth_df


def run_study(tierB_dir, configs=None, n_boot=80, seed=0,
              results_dir=None, write=True):
    """Run the grid over the Tier-B suite, join truth, and persist results.

    Each fitted row is joined to its truth by ``case_id``, selecting the truth
    field that MATCHES the config's intensity definition
    (``true_id_ig = true_id_ig_area`` for area configs, ``true_id_ig_height``
    for height configs).  Adds ``error = id_ig - true_id_ig`` and
    ``abs_error = |error|``.  Writes results to ``results_dir`` as BOTH parquet
    and csv (directory created if needed).  Returns the result DataFrame.
    """
    spectra, truth_df = _load_tierB_suite(tierB_dir)
    df = run_grid(spectra, configs=configs, n_boot=n_boot, seed=seed)

    # Truth join on case_id; pick the matched-definition truth column.
    df = df.merge(truth_df, on="case_id", how="left")
    matched_truth = np.where(
        df["intensity"].to_numpy() == "area",
        df["true_id_ig_area"].to_numpy(),
        df["true_id_ig_height"].to_numpy(),
    )
    df["true_id_ig"] = matched_truth.astype(float)
    df["error"] = df["id_ig"] - df["true_id_ig"]
    df["abs_error"] = df["error"].abs()
    df = df.drop(columns=["true_id_ig_area", "true_id_ig_height"])

    # Enforce the frozen column order.
    df = df[list(RESULT_COLUMNS)]

    if write:
        if results_dir is None:
            results_dir = os.path.join(
                os.path.dirname(tierB_dir.rstrip("/")), "results"
            )
        os.makedirs(results_dir, exist_ok=True)
        df.to_parquet(os.path.join(results_dir, "tierB_grid_results.parquet"))
        df.to_csv(
            os.path.join(results_dir, "tierB_grid_results.csv"), index=False
        )
    return df


# --------------------------------------------------------------------------- #
# DESCRIPTIVE decomposition (explicitly non-causal)
# --------------------------------------------------------------------------- #
def decompose(df):
    """DESCRIPTIVE spread summary of grid results (NOT causal / NOT ANOVA).

    This is a purely DESCRIPTIVE accounting of where I_D/I_G estimates and their
    errors spread across configurations.  It assigns NO causal attribution and
    performs NO inferential variance partition: the per-factor level means are
    marginal descriptive summaries only, confounded by the factorial layout, and
    must not be read as main effects.

    Returns a dict with: ``sigma_meth`` (sd of ``error`` across configs),
    ``id_ig_sd`` (sd of ``id_ig`` across configs), an R-style ``range`` of
    ``error``, ``per_factor`` (mean ``abs_error`` grouped by each of the 5
    factors), and a ``label`` field that names the summary DESCRIPTIVE.
    """
    err = df["error"].to_numpy(dtype=float)
    err = err[np.isfinite(err)]
    idig = df["id_ig"].to_numpy(dtype=float)
    idig = idig[np.isfinite(idig)]

    per_factor = {}
    for factor in ("baseline", "lineshape", "bwf_g", "peak_set", "intensity"):
        per_factor[factor] = df.groupby(factor)["abs_error"].mean().to_dict()

    return {
        "label": "DESCRIPTIVE spread summary (non-causal, not ANOVA)",
        "sigma_meth": float(np.std(err)) if err.size else float("nan"),
        "id_ig_sd": float(np.std(idig)) if idig.size else float("nan"),
        "range": (
            (float(np.min(err)), float(np.max(err))) if err.size
            else (float("nan"), float("nan"))
        ),
        "per_factor": per_factor,
    }


# --------------------------------------------------------------------------- #
# Q1 ranking
# --------------------------------------------------------------------------- #
def _config_key_columns():
    return ["baseline", "lineshape", "bwf_g", "peak_set", "intensity"]


def rank_configurations(df, coverage_floor=COVERAGE_FLOOR,
                        max_fail=MAX_FAILURE_RATE):
    """Q1 ranking per (material_class, SNR regime) (T5 fragment).

    Implements docs/validation_plan.md Section 3: within each
    (``material_class``, ``snr_label``) regime, EXCLUDE configurations whose
    empirical 95% coverage is below ``coverage_floor`` OR whose failure rate
    exceeds ``max_fail``, then order the survivors by RMSE of the I_D/I_G error
    ascending.  Ineligible configurations are dropped (not ranked last).

    Empirical coverage = fraction of spectra in the regime whose ``true_id_ig``
    lies within ``[lo95, hi95]``.  Failure rate = fraction of spectra whose
    primary fit failed (non-finite ``id_ig``).  RMSE = root-mean-square of the
    finite ``error`` values.
    """
    cfg_cols = _config_key_columns()
    out_rows = []
    for (mat, snr), regime in df.groupby(["material_class", "snr_label"]):
        for keys, grp in regime.groupby(cfg_cols):
            idig = grp["id_ig"].to_numpy(dtype=float)
            lo = grp["lo95"].to_numpy(dtype=float)
            hi = grp["hi95"].to_numpy(dtype=float)
            true = grp["true_id_ig"].to_numpy(dtype=float)
            err = grp["error"].to_numpy(dtype=float)

            n = len(grp)
            failed = ~np.isfinite(idig)
            failure_rate = float(np.mean(failed)) if n else 1.0

            covered = (
                np.isfinite(lo) & np.isfinite(hi) & np.isfinite(true)
                & (true >= lo) & (true <= hi)
            )
            coverage = float(np.mean(covered)) if n else 0.0

            fin_err = err[np.isfinite(err)]
            rmse = (
                float(np.sqrt(np.mean(fin_err**2))) if fin_err.size
                else float("nan")
            )

            eligible = (coverage >= coverage_floor) and (failure_rate <= max_fail)

            row = dict(zip(cfg_cols, keys))
            row.update(
                {
                    "material_class": mat,
                    "snr_label": snr,
                    "n_spectra": n,
                    "rmse": rmse,
                    "coverage": coverage,
                    "failure_rate": failure_rate,
                    "eligible": eligible,
                }
            )
            out_rows.append(row)

    table = pd.DataFrame(out_rows)
    if table.empty:
        table["rank"] = []
        return table

    # Eligible survivors only, ranked by RMSE ascending within each regime.
    survivors = table[table["eligible"]].copy()
    survivors = survivors[np.isfinite(survivors["rmse"].to_numpy(dtype=float))]
    survivors = survivors.sort_values(
        ["material_class", "snr_label", "rmse"]
    ).reset_index(drop=True)
    survivors["rank"] = (
        survivors.groupby(["material_class", "snr_label"])["rmse"]
        .rank(method="first")
        .astype(int)
    )
    return survivors


__all__ = [
    "RESULT_COLUMNS",
    "COVERAGE_FLOOR",
    "MAX_FAILURE_RATE",
    "BASELINES",
    "LINESHAPES",
    "PEAK_SETS",
    "INTENSITIES",
    "default_grid",
    "run_grid",
    "run_study",
    "decompose",
    "rank_configurations",
]
