"""Selector-audit unit tests, including Gate V4 (exact rigged-case recovery).

Gate V4 asserts that the audit machinery recovers, EXACTLY (to floating-point
epsilon), the answers that are known by hand on two rigged spectra: a perfectly
correlated frame (rho = +1, top-1 regret = 0) and a perfectly anti-correlated
frame (rho = -1). A separate test checks that ties are handled with AVERAGE
ranks (the scipy.stats.spearmanr convention), not ordinal/first-occurrence ranks.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import rankdata, spearmanr

from ramanuq.selectors import _spectrum_units, audit, rigged_cases, score_configs

EPS = 1e-12


@pytest.mark.validation
def test_v4_rigged_correlated_exact_recovery():
    """Correlated rigged frame: rho == +1.0 and top-1 regret == 0.0 exactly."""
    correlated, _anti = rigged_cases()
    t6 = audit(correlated)
    # Every (stratum, selector) cell must show the exact correlated answer.
    assert not t6.empty
    np.testing.assert_allclose(
        t6["rho_median"].to_numpy(dtype=float), 1.0, rtol=0.0, atol=EPS
    )
    np.testing.assert_allclose(
        t6["regret_median"].to_numpy(dtype=float), 0.0, rtol=0.0, atol=EPS
    )


@pytest.mark.validation
def test_v4_rigged_anticorrelated_exact_recovery():
    """Anti-correlated rigged frame: rho == -1.0 exactly."""
    _correlated, anti = rigged_cases()
    t6 = audit(anti)
    assert not t6.empty
    np.testing.assert_allclose(
        t6["rho_median"].to_numpy(dtype=float), -1.0, rtol=0.0, atol=EPS
    )


@pytest.mark.validation
def test_v4_score_configs_primitive_exact():
    """The primitive itself returns the exact hand-known values on rigged data."""
    sel = np.arange(1.0, 9.0)
    abs_err = np.linspace(0.1, 0.8, 8)
    corr = score_configs(sel, abs_err)
    assert abs(corr.rho - 1.0) < EPS
    assert abs(corr.top1_regret - 0.0) < EPS
    assert corr.top_quartile_hit == 1.0  # selector-min == oracle, most accurate

    anti = score_configs(sel, abs_err[::-1])
    assert abs(anti.rho - (-1.0)) < EPS
    # selector-min config is the WORST here: regret == full spread, no hit.
    assert abs(anti.top1_regret - (abs_err.max() - abs_err.min())) < EPS
    assert anti.top_quartile_hit == 0.0


def test_average_rank_tie_handling():
    """Deliberate ties yield the AVERAGE-rank Spearman, not ordinal ranks."""
    # Two tied selector values; average ranks -> [1.5, 1.5, 3, 4].
    sel = np.array([1.0, 1.0, 3.0, 4.0])
    abs_err = np.array([0.4, 0.1, 0.2, 0.9])

    got = score_configs(sel, abs_err).rho

    # Reference: scipy spearmanr (average-rank by definition).
    ref_scipy = float(spearmanr(sel, abs_err).correlation)
    # Reference: Pearson correlation of AVERAGE ranks, computed independently.
    ref_avg = float(
        np.corrcoef(
            rankdata(sel, method="average"), rankdata(abs_err, method="average")
        )[0, 1]
    )
    # The ordinal (first-occurrence) tie convention would give a DIFFERENT value.
    ord_val = float(
        np.corrcoef(
            rankdata(sel, method="ordinal"), rankdata(abs_err, method="ordinal")
        )[0, 1]
    )

    assert abs(got - ref_scipy) < 1e-12
    assert abs(got - ref_avg) < 1e-12
    assert abs(got - ord_val) > 1e-6, "result must reflect average-rank, not ordinal"


def test_cx4_nonfinite_selector_config_excluded_before_scoring():
    """CX-4: a config with finite id_ig/abs_error but a NaN selector value is
    dropped from the SHARED surviving set, so argmin/spearmanr stay sane.

    The bad row carries a NaN in ``aic`` only, yet must be excluded for EVERY
    selector (the surviving set is shared): without the fix it would survive,
    np.argmin would pick the NaN as the bogus selector-min and spearmanr would
    return NaN for the whole spectrum.
    """
    selectors = ("redchi", "aic", "bic")
    sel = np.array([1.0, 2.0, 3.0, 4.0])
    abs_err = np.array([0.1, 0.2, 0.3, 0.4])
    group = pd.DataFrame(
        {
            "case_id": ["c0"] * 4,
            "material_class": ["m"] * 4,
            "snr_label": [50] * 4,
            "peak_set": ["DG"] * 4,
            "id_ig": 1.0 + abs_err,  # all finite
            "redchi": sel,
            "aic": [1.0, np.nan, 3.0, 4.0],  # one failed-fit selector value
            "bic": sel,
            "abs_error": abs_err,  # all finite
        }
    )

    rows = _spectrum_units(group, selectors, strata=("full",))
    assert rows, "expected one row per selector"
    # All selectors share the SAME surviving set: 4 configs minus the NaN row.
    for r in rows:
        assert r["n_configs"] == 3, "the NaN-selector config must be excluded"
        assert np.isfinite(r["rho"]), "rho must be finite, not NaN"


def test_coverage_under_misspecification_inclusive_endpoints():
    """Endpoints counted inclusively; a point exactly on a bound is covered."""
    from ramanuq.selectors import coverage_under_misspecification
    import pandas as pd

    df = pd.DataFrame(
        {
            "material_class": ["m"] * 4,
            "snr_label": [50] * 4,
            "lo95": [0.0, 0.0, 0.0, np.nan],
            "hi95": [1.0, 1.0, 1.0, 1.0],
            "true_id_ig": [0.0, 1.0, 2.0, 0.5],  # on-lo, on-hi, outside, nan-lo
        }
    )
    t6b = coverage_under_misspecification(df)
    assert t6b.shape[0] == 1
    # 3 finite rows; the on-lo and on-hi rows are covered, the outside is not.
    assert t6b["n"].iloc[0] == 3
    assert abs(t6b["coverage"].iloc[0] - (2.0 / 3.0)) < 1e-12
