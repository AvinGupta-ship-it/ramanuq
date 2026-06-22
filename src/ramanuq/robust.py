"""Jackknife (leave-one-out) stability analysis of the Q1 ranking (Q1b).

This implements the Q1b jackknife from docs/validation_plan.md Section 3: the
per-regime ranking is recomputed under leave-one-out over (a) configuration
families -- dropping each baseline class, each lineshape, and each peak set in
turn -- and (b) suite instances -- dropping each random instance in turn. For
the protocol-recommended configuration (the full-ranking rank-1 per regime) it
reports per regime: top-quartile retention frequency, rank IQR, and a flip flag.

All study-frame column reads use only names in :data:`ramanuq.grid.RESULT_COLUMNS`
(the single source of truth for the schema). The ranking-output column ``rank``
and this module's own output columns are declared explicitly below.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .grid import (
    COVERAGE_FLOOR,
    MAX_FAILURE_RATE,
    rank_configurations,
)

# The five configuration factors that identify a configuration.
CONFIG_FACTORS = ("baseline", "lineshape", "bwf_g", "peak_set", "intensity")
# Configuration "families" jackknifed in leave-one-out (Section 3a).
FAMILY_FACTORS = ("baseline", "lineshape", "peak_set")
# Regime keys.
REGIME_KEYS = ("material_class", "snr_label")

# The only ranking-output column this module reads that is not in
# grid.RESULT_COLUMNS (it is produced by grid.rank_configurations).
RANK_COLUMN = "rank"
# Output columns this module creates for its T9 fragment.
OUTPUT_COLUMNS = (
    "top_quartile_retention",
    "rank_iqr",
    "flip_flag",
    "n_resamples",
)


def _config_tuple(row):
    return tuple(row[f] for f in CONFIG_FACTORS)


def _config_present(regime_df, cfg):
    """Whether ``cfg`` (a 5-factor tuple) has any row in ``regime_df``."""
    mask = np.ones(len(regime_df), dtype=bool)
    for factor, value in zip(CONFIG_FACTORS, cfg):
        mask &= regime_df[factor].to_numpy() == value
    return bool(mask.any())


def _match_config(ranked_regime, cfg):
    """Rows of a per-regime ranking table matching ``cfg``."""
    mask = np.ones(len(ranked_regime), dtype=bool)
    for factor, value in zip(CONFIG_FACTORS, cfg):
        mask &= ranked_regime[factor].to_numpy() == value
    return ranked_regime[mask]


def _resamples(study_df):
    """Leave-one-out resamples: family drops then instance drops.

    Returns a list of ``(label, sub_df)`` pairs.
    """
    out = []
    for factor in FAMILY_FACTORS:
        for value in sorted(study_df[factor].unique()):
            out.append(
                (f"drop_{factor}={value}", study_df[study_df[factor] != value])
            )
    for value in sorted(study_df["instance"].unique()):
        out.append(
            (f"drop_instance={value}", study_df[study_df["instance"] != value])
        )
    return out


def _iqr(values):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, 75) - np.percentile(arr, 25))


def jackknife_ranking(study_df, coverage_floor=COVERAGE_FLOOR,
                      max_fail=MAX_FAILURE_RATE):
    """Q1b jackknife stability of the protocol-recommended configuration.

    For each regime, the recommended configuration is the rank-1 entry of the
    full ranking.  Each leave-one-out resample's ranking is recomputed and, for
    every resample in which the recommended configuration is still present in
    the regime, the following are accumulated:

    - ``top_quartile_retention``: fraction of (applicable) resamples in which the
      recommended config's rank is within the regime's top quartile.
    - ``rank_iqr``: interquartile range of the recommended config's rank across
      (applicable) resamples.  A resample in which the config is present but
      becomes rank-ineligible contributes a worst-rank sentinel.
    - ``flip_flag``: ``True`` if the regime's rank-1 recommendation changes in
      any applicable resample.

    Resamples that remove the recommended configuration entirely (e.g. dropping
    its own family level) are not applicable to that config and are skipped.
    Returns the T9 fragment as a DataFrame.
    """
    full = rank_configurations(study_df, coverage_floor, max_fail)
    resamples = _resamples(study_df)

    rows = []
    if full.empty:
        return pd.DataFrame(rows)

    recommended = full[full[RANK_COLUMN] == 1]
    for _, rec in recommended.iterrows():
        mat = rec["material_class"]
        snr = rec["snr_label"]
        rec_cfg = _config_tuple(rec)

        ranks = []
        retention_hits = 0
        applicable = 0
        flip = False

        for _label, sub in resamples:
            regime_sub = sub[
                (sub["material_class"] == mat) & (sub["snr_label"] == snr)
            ]
            if not _config_present(regime_sub, rec_cfg):
                continue  # recommended config not in this resample -> N/A
            applicable += 1

            sub_rank = rank_configurations(sub, coverage_floor, max_fail)
            regime_rank = sub_rank[
                (sub_rank["material_class"] == mat)
                & (sub_rank["snr_label"] == snr)
            ]
            n_elig = len(regime_rank)

            cfg_rows = _match_config(regime_rank, rec_cfg)
            if len(cfg_rows):
                cfg_rank = int(cfg_rows.iloc[0][RANK_COLUMN])
            else:
                # Present in the resample but failed an eligibility gate.
                cfg_rank = n_elig + 1
            ranks.append(cfg_rank)

            tq_threshold = math.ceil(n_elig / 4) if n_elig else 0
            if cfg_rank <= tq_threshold:
                retention_hits += 1

            top = regime_rank[regime_rank[RANK_COLUMN] == 1]
            if len(top) == 0 or _config_tuple(top.iloc[0]) != rec_cfg:
                flip = True

        retention = (
            retention_hits / applicable if applicable else float("nan")
        )
        row = dict(zip(CONFIG_FACTORS, rec_cfg))
        row.update(
            {
                "material_class": mat,
                "snr_label": snr,
                "top_quartile_retention": retention,
                "rank_iqr": _iqr(ranks),
                "flip_flag": bool(flip),
                "n_resamples": applicable,
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)


__all__ = [
    "CONFIG_FACTORS",
    "FAMILY_FACTORS",
    "RANK_COLUMN",
    "OUTPUT_COLUMNS",
    "jackknife_ranking",
]
