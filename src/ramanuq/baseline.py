"""Baseline (background) estimation for spectra.

A single entry point :func:`estimate` supports polynomial baselines
(``linear``, ``poly3``, ``poly5``) and an asymmetric-least-squares baseline
(``als``, the Eilers-Boelens algorithm).  Every method returns a finite
baseline array of the same length as the spectrum, plus a diagnostics dict.

The ``none`` method returns an all-zero baseline (a no-op subtraction).  It
exists so the pipeline can fit data that is already baseline-free -- in
particular the Tier-A Gate V1 recovery spectra, where any nonzero baseline
estimate would bias the recovered band areas.  ``none`` is deliberately *not*
part of the studied baseline grid (it is not a background-estimation method); it
must not be added to the configuration grid used for the Q1/Q2 studies.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

_POLY_DEGREE = {"linear": 1, "poly3": 3, "poly5": 5}

# Eilers-Boelens ALS defaults.
_ALS_LAM = 1e5
_ALS_P = 0.01
_ALS_NITER = 10

# Tiny diagonal ridge added to the ALS normal-equations matrix so the solve is
# never exactly singular.  On a perfectly flat spectrum the asymmetric weights
# all collapse to zero (no point is strictly above or below the smooth), leaving
# only lam * D^T D, which is rank-deficient by two (its null space is the
# constant and linear ramps).  That singular solve returns non-finite values on
# some LAPACK backends (Linux CI) while returning finite values on others
# (macOS).  The ridge makes the system positive-definite, so the solve is finite
# on every backend; at 1e-9 it is many orders below the smallest weight (p) and
# does not perturb well-conditioned fits.
_ALS_RIDGE = 1e-9


def _poly_baseline(x, y, degree):
    """Least-squares polynomial baseline of the given degree."""
    # Center/scale x for conditioning of the Vandermonde fit.
    xs = (x - np.mean(x)) / (np.std(x) or 1.0)
    coeffs = np.polyfit(xs, y, degree)
    return np.polyval(coeffs, xs), coeffs


def _als_baseline(y, lam, p, niter):
    """Asymmetric least squares baseline (Eilers & Boelens)."""
    n = len(y)
    # Second-order difference operator.
    d = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(n - 2, n), format="csc")
    dtd = lam * (d.T @ d)
    # Diagonal ridge keeps wmat + dtd positive-definite even when every weight
    # collapses to zero (flat input), so the solve never goes singular.
    ridge = _ALS_RIDGE * sparse.eye(n, format="csc")
    w = np.ones(n)
    z = y.copy()
    for _ in range(niter):
        wmat = sparse.diags(w, 0, format="csc")
        z = spsolve(wmat + dtd + ridge, w * y)
        w = p * (y > z) + (1.0 - p) * (y < z)
    return z


def estimate(spec, method, **p):
    """Estimate a baseline for ``spec`` using ``method``.

    Parameters
    ----------
    spec:
        A :class:`ramanuq.io.Spectrum`.
    method:
        One of ``{"none", "linear", "poly3", "poly5", "als"}``.  ``none``
        returns an all-zero baseline (no-op), for already-baseline-free input.
    **p:
        Method-specific overrides.  For ``als``: ``lam`` (default 1e5),
        ``p`` (default 0.01), ``niter`` (default 10).

    Returns
    -------
    (baseline, diagnostics):
        ``baseline`` is a finite ndarray; ``diagnostics`` is a dict describing
        the method and its effective parameters.
    """
    x = np.asarray(spec.shift, dtype=float)
    y = np.asarray(spec.intensity, dtype=float)

    if method == "none":
        # No-op baseline: an exact zero array.  Used only for already
        # baseline-free input (e.g. the Gate V1 recovery path); does not touch
        # any of the estimating methods below.
        baseline = np.zeros_like(y)
        diagnostics = {"method": "none"}
    elif method in _POLY_DEGREE:
        degree = _POLY_DEGREE[method]
        baseline, coeffs = _poly_baseline(x, y, degree)
        diagnostics = {"method": method, "degree": degree, "coeffs": coeffs}
    elif method == "als":
        lam = float(p.get("lam", _ALS_LAM))
        p_asym = float(p.get("p", _ALS_P))
        niter = int(p.get("niter", _ALS_NITER))
        baseline = _als_baseline(y, lam, p_asym, niter)
        diagnostics = {"method": "als", "lam": lam, "p": p_asym, "niter": niter}
    else:
        raise ValueError(
            f"unknown baseline method {method!r}; "
            "expected one of none, linear, poly3, poly5, als"
        )

    baseline = np.asarray(baseline, dtype=float)
    if not np.all(np.isfinite(baseline)):
        raise ValueError(f"baseline method {method!r} produced non-finite values")
    return baseline, diagnostics
