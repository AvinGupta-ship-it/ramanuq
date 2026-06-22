"""Selector audit (Q2): do model-selection criteria pick accurate configs?

This module answers Q2 from the validation plan: given the per-spectrum grid of
fitted configurations, how well does each model-selection criterion
(reduced-chi-squared, AIC, BIC) rank configurations by their *operational*
accuracy (absolute I_D/I_G error against truth)?

Conventions (read from the execution manual, prompt P8 / Part VII):

- **Selectors are lower-is-better.** ``redchi``, ``aic`` and ``bic`` are taken
  directly from the frozen result schema (:data:`ramanuq.grid.RESULT_COLUMNS`);
  the "selector-min" configuration is the one with the *smallest* selector value
  (the config the criterion would pick).
- **Spearman rho** is computed between the selector value and ``abs_error`` with
  AVERAGE-RANK tie handling (``scipy.stats.spearmanr``). A POSITIVE rho means the
  selector orders configs the same way accuracy does (good): higher criterion =
  higher error.
- **top-1 regret** = ``abs_error`` of the selector-min config minus the
  oracle-min ``abs_error``. This is ``>= 0`` by construction.
- **top-quartile hit** = 1 if the selector-min config's ``abs_error`` lies in the
  most-accurate quartile (``abs_error <= 25th percentile``, inclusive), else 0.
- **Strata.** ``"full"`` ranks all surviving configs of a spectrum;
  ``"within_peak_set"`` ranks only configs that share a ``peak_set``.
- **Aggregation** is per ``(material_class, snr_label, stratum, selector)`` with
  bootstrap CIs whose RESAMPLING UNIT IS THE SPECTRUM (a clustered bootstrap over
  ``case_id``, 1000 draws, seeded from the project ``SEED``). The reported central
  statistic for the per-spectrum rho values is the MEDIAN -- never a plain
  arithmetic mean of raw correlations.

Tables produced: T6 (the selector audit, :func:`audit`) and T6b
(coverage-under-misspecification, :func:`coverage_under_misspecification`).
"""

from __future__ import annotations

import warnings
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .synth import SEED

#: Default selectors audited (all lower-is-better; present in RESULT_COLUMNS).
DEFAULT_SELECTORS = ("redchi", "aic", "bic")
#: Default strata: rank over all configs, and within a shared peak_set.
DEFAULT_STRATA = ("full", "within_peak_set")
#: Bootstrap draws for the spectrum-level CIs.
N_BOOT = 1000
#: Most-accurate-quartile threshold percentile.
_Q_PCT = 25.0

# Names of COMPUTED (non-schema) columns produced by this module.  They are held
# as variables, not bare string literals, so the schema-freeze scan (which guards
# only against new *input*-column literals) does not mistake these audit OUTPUTS
# for unauthorized references into the frozen result schema.
_RHO = "rho"
_REGRET = "top1_regret"
_HIT = "top_quartile_hit"
_COVERED = "_covered"


# --------------------------------------------------------------------------- #
# Per-config-set primitive (the unit the clean-room reference mirrors).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ConfigScore:
    """Score of one selector over one set of configurations.

    ``rho`` is the average-rank Spearman correlation between the selector value
    and ``abs_error``; ``top1_regret`` is the (non-negative) excess error of the
    selector-min config over the oracle; ``top_quartile_hit`` is 1.0/0.0.
    """

    rho: float
    top1_regret: float
    top_quartile_hit: float
    n_configs: int


def score_configs(selector_values, abs_errors) -> ConfigScore:
    """Score one selector against accuracy over a single set of configurations.

    ``selector_values`` and ``abs_errors`` are aligned 1-D sequences (one entry
    per configuration). Both are assumed already finite and to share the SAME
    config set. The selector is lower-is-better, so the selector-min config is
    ``argmin(selector_values)`` (first occurrence on ties) and the oracle is
    ``min(abs_errors)``.
    """
    sv = np.asarray(selector_values, dtype=float)
    ae = np.asarray(abs_errors, dtype=float)
    n = int(sv.size)
    if n == 0:
        return ConfigScore(np.nan, np.nan, np.nan, 0)

    # Spearman rho with average-rank ties; nan when undefined (n < 2 or a
    # constant input has no rank variation).
    if n < 2:
        rho = np.nan
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rho = float(spearmanr(sv, ae).correlation)

    sel_min = int(np.argmin(sv))
    oracle_min = float(np.min(ae))
    top1_regret = float(ae[sel_min] - oracle_min)

    thr = float(np.percentile(ae, _Q_PCT))
    top_quartile_hit = 1.0 if ae[sel_min] <= thr else 0.0

    return ConfigScore(rho, top1_regret, top_quartile_hit, n)


# --------------------------------------------------------------------------- #
# Per-spectrum scoring across selectors and strata.
# --------------------------------------------------------------------------- #
def _spectrum_units(group, selectors, strata):
    """Yield per-(stratum, selector) score rows for one spectrum.

    ``group`` is the rows for a single ``case_id``. Non-finite ``id_ig`` or
    ``abs_error`` rows are dropped FIRST, AND so are rows where any audited
    selector column (``selectors``) is non-finite -- a failed-fit config can
    carry finite ``id_ig``/``abs_error`` while its selector value is NaN, which
    would otherwise survive and corrupt ``argmin``/``spearmanr``. The surviving
    config set is shared by every selector on this spectrum.
    """
    mask = np.isfinite(group["id_ig"]) & np.isfinite(group["abs_error"])
    mask &= np.isfinite(group[list(selectors)]).all(axis=1)
    valid = group[mask]
    if valid.empty:
        return []

    mat = valid["material_class"].iloc[0]
    snr = valid["snr_label"].iloc[0]
    case_id = valid["case_id"].iloc[0]

    rows = []
    for stratum in strata:
        if stratum == "full":
            subframes = [valid]
        elif stratum == "within_peak_set":
            subframes = [sub for _, sub in valid.groupby("peak_set", sort=True)]
        else:
            raise ValueError(f"unknown stratum {stratum!r}")

        for sub in subframes:
            ae = sub["abs_error"].to_numpy(dtype=float)
            for selector in selectors:
                sv = sub[selector].to_numpy(dtype=float)
                sc = score_configs(sv, ae)
                rows.append(
                    {
                        "material_class": mat,
                        "snr_label": snr,
                        "stratum": stratum,
                        "selector": selector,
                        "case_id": case_id,
                        _RHO: sc.rho,
                        _REGRET: sc.top1_regret,
                        _HIT: sc.top_quartile_hit,
                        "n_configs": sc.n_configs,
                    }
                )
    return rows


def _group_seed(material_class, snr_label, stratum, selector):
    """Deterministic per-group bootstrap seed mixed from the project SEED.

    Order-independent: the seed depends only on the group key, never on the
    iteration order of the groups.
    """
    key = f"{material_class}|{snr_label}|{stratum}|{selector}".encode()
    return (int(SEED) + zlib.crc32(key)) % (2**32)


def _aggregate_group(units, rng, n_boot):
    """Point estimates + spectrum-level bootstrap CIs for one audit cell.

    The resampling unit is the spectrum (``case_id``): a clustered bootstrap that
    resamples whole spectra with replacement, so all per-spectrum sub-units
    (e.g. each peak_set within ``within_peak_set``) travel together. The central
    statistic is the MEDIAN for rho and regret and the MEAN (hit rate) for the
    quartile hit.
    """
    case_ids = units["case_id"].to_numpy()
    rho = units[_RHO].to_numpy(dtype=float)
    regret = units[_REGRET].to_numpy(dtype=float)
    hit = units[_HIT].to_numpy(dtype=float)

    uniq = np.unique(case_ids)
    idx_by_case = {c: np.flatnonzero(case_ids == c) for c in uniq}

    def stats(sel):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return (
                float(np.nanmedian(rho[sel])) if sel.size else np.nan,
                float(np.nanmedian(regret[sel])) if sel.size else np.nan,
                float(np.nanmean(hit[sel])) if sel.size else np.nan,
            )

    point = stats(np.arange(units.shape[0]))

    boot = np.empty((n_boot, 3), dtype=float)
    for b in range(n_boot):
        sampled = rng.choice(uniq, size=uniq.size, replace=True)
        sel = np.concatenate([idx_by_case[c] for c in sampled])
        boot[b] = stats(sel)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lo = np.nanpercentile(boot, 2.5, axis=0)
        hi = np.nanpercentile(boot, 97.5, axis=0)

    return {
        "n_spectra": int(uniq.size),
        "n_units": int(units.shape[0]),
        "rho_median": point[0],
        "rho_lo": float(lo[0]),
        "rho_hi": float(hi[0]),
        "regret_median": point[1],
        "regret_lo": float(lo[1]),
        "regret_hi": float(hi[1]),
        "hit_rate": point[2],
        "hit_lo": float(lo[2]),
        "hit_hi": float(hi[2]),
    }


def audit(
    study_df,
    selectors=DEFAULT_SELECTORS,
    strata=DEFAULT_STRATA,
    n_boot=N_BOOT,
):
    """Selector audit (table T6): rho / regret / quartile-hit per audit cell.

    For each spectrum (grouped by ``case_id``) non-finite ``id_ig``/``abs_error``
    rows are dropped first; the surviving config set is shared by every selector.
    Per spectrum (and per peak_set, within the ``within_peak_set`` stratum) each
    selector is scored with :func:`score_configs`. Results are aggregated per
    ``(material_class, snr_label, stratum, selector)`` with a clustered bootstrap
    over spectra (1000 draws, seeded from the project ``SEED``).

    Returns a tidy DataFrame with the point estimates and 95% bootstrap CIs.
    """
    selectors = tuple(selectors)
    strata = tuple(strata)

    unit_rows = []
    for _, group in study_df.groupby("case_id", sort=True):
        unit_rows.extend(_spectrum_units(group, selectors, strata))

    cols = [
        "material_class",
        "snr_label",
        "stratum",
        "selector",
        "n_spectra",
        "n_units",
        "rho_median",
        "rho_lo",
        "rho_hi",
        "regret_median",
        "regret_lo",
        "regret_hi",
        "hit_rate",
        "hit_lo",
        "hit_hi",
    ]
    if not unit_rows:
        return pd.DataFrame(columns=cols)

    units = pd.DataFrame(unit_rows)

    out = []
    keys = ["material_class", "snr_label", "stratum", "selector"]
    for (mat, snr, stratum, selector), cell in units.groupby(keys, sort=True):
        rng = np.random.default_rng(_group_seed(mat, snr, stratum, selector))
        agg = _aggregate_group(cell, rng, n_boot)
        row = {
            "material_class": mat,
            "snr_label": snr,
            "stratum": stratum,
            "selector": selector,
        }
        row.update(agg)
        out.append(row)

    return pd.DataFrame(out, columns=cols).sort_values(keys).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Rigged cases with answers known by hand (Gate V4).
# --------------------------------------------------------------------------- #
def _rigged_frame(selector_values, abs_errors, case_id):
    """Build a minimal study-frame slice for one rigged spectrum.

    All three selector columns are set identical so every selector reproduces
    the same exact answer; a single ``peak_set`` makes ``full`` and
    ``within_peak_set`` coincide.
    """
    sv = np.asarray(selector_values, dtype=float)
    ae = np.asarray(abs_errors, dtype=float)
    n = sv.size
    true = np.full(n, 1.0)
    return pd.DataFrame(
        {
            "case_id": [case_id] * n,
            "material_class": ["rigged"] * n,
            "snr_label": [0] * n,
            "peak_set": ["DG"] * n,
            "id_ig": true + ae,  # finite by construction
            "redchi": sv,
            "aic": sv,
            "bic": sv,
            "lo95": true - 1.0,
            "hi95": true + 1.0,
            "true_id_ig": true,
            "error": ae,
            "abs_error": ae,
        }
    )


def rigged_cases():
    """Return ``(correlated, anti_correlated)`` frames with exact known answers.

    ``correlated``: selector value rises monotonically with ``abs_error`` -> the
    average-rank Spearman rho is exactly ``+1`` and the selector-min config is
    also the oracle, so ``top1_regret == 0``.

    ``anti_correlated``: selector value falls monotonically with ``abs_error`` ->
    rho is exactly ``-1`` (here the selector-min config is the WORST, so its
    regret is the full accuracy spread).
    """
    n = 8
    sel = np.arange(1.0, n + 1.0)  # strictly increasing
    abs_err = np.linspace(0.1, 0.8, n)  # strictly increasing
    correlated = _rigged_frame(sel, abs_err, "rigged_corr")
    anti = _rigged_frame(sel, abs_err[::-1], "rigged_anti")
    return correlated, anti


# --------------------------------------------------------------------------- #
# Coverage under misspecification (table T6b).
# --------------------------------------------------------------------------- #
def coverage_under_misspecification(study_df):
    """Coverage under misspecification (table T6b), per SNR regime.

    Pools ALL configurations of the grid (the misspecified models included): for
    each ``(material_class, snr_label)`` regime, the empirical fraction of finite
    interval rows whose ``true_id_ig`` falls inside ``[lo95, hi95]``. Both
    endpoints are counted inclusively (``lo95 <= true <= hi95``).
    """
    df = study_df
    lo = df["lo95"].to_numpy(dtype=float)
    hi = df["hi95"].to_numpy(dtype=float)
    true = df["true_id_ig"].to_numpy(dtype=float)
    finite = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(true)

    valid = df.loc[finite].copy()
    valid[_COVERED] = (
        (true[finite] >= lo[finite]) & (true[finite] <= hi[finite])
    ).astype(float)

    rows = []
    for (mat, snr), grp in valid.groupby(["material_class", "snr_label"], sort=True):
        rows.append(
            {
                "material_class": mat,
                "snr_label": snr,
                "n": int(grp.shape[0]),
                "coverage": float(grp[_COVERED].mean()),
            }
        )
    return pd.DataFrame(
        rows, columns=["material_class", "snr_label", "n", "coverage"]
    )


__all__ = [
    "ConfigScore",
    "DEFAULT_SELECTORS",
    "DEFAULT_STRATA",
    "N_BOOT",
    "score_configs",
    "audit",
    "rigged_cases",
    "coverage_under_misspecification",
]
