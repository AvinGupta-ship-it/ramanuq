"""Baseline (background) estimation for spectra.

A single entry point :func:`estimate` supports polynomial baselines
(``linear``, ``poly3``, ``poly5``) and an asymmetric-least-squares baseline
(``als``, the Eilers-Boelens algorithm).  Every method returns a finite
baseline array of the same length as the spectrum, plus a diagnostics dict.
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
    w = np.ones(n)
    z = y.copy()
    for _ in range(niter):
        wmat = sparse.diags(w, 0, format="csc")
        z = spsolve(wmat + dtd, w * y)
        w = p * (y > z) + (1.0 - p) * (y < z)
    return z


def estimate(spec, method, **p):
    """Estimate a baseline for ``spec`` using ``method``.

    Parameters
    ----------
    spec:
        A :class:`ramanuq.io.Spectrum`.
    method:
        One of ``{"linear", "poly3", "poly5", "als"}``.
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

    if method in _POLY_DEGREE:
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
            "expected one of linear, poly3, poly5, als"
        )

    baseline = np.asarray(baseline, dtype=float)
    if not np.all(np.isfinite(baseline)):
        raise ValueError(f"baseline method {method!r} produced non-finite values")
    return baseline, diagnostics
