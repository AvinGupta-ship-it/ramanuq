"""Fitting pipeline: despike -> baseline subtract -> bounded WLS -> bootstrap.

The pipeline never raises on non-convergence.  A failed primary fit is recorded
in the result (NaN statistics, ``meta['success'] = False``); failed bootstrap
refits are counted in ``n_failed``.  Parameter uncertainties come from a
residual bootstrap on the fitted residuals, summarized as percentile intervals.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import baseline as baseline_mod
from .despike import despike
from .io import Spectrum
from .model import build_model

_TINY = 1e-300


# --------------------------------------------------------------------------- #
# Information criteria (importable for differential testing)
# --------------------------------------------------------------------------- #
def aic(n, k, rss):
    """Akaike information criterion: ``n*ln(rss/n) + 2k`` (natural log)."""
    return n * np.log(rss / n) + 2 * k


def bic(n, k, rss):
    """Bayesian information criterion: ``n*ln(rss/n) + k*ln(n)`` (natural log)."""
    return n * np.log(rss / n) + k * np.log(n)


# --------------------------------------------------------------------------- #
# Configuration and result containers
# --------------------------------------------------------------------------- #
@dataclass
class PipelineConfig:
    """Configuration for :func:`fit_spectrum`."""

    peak_set: str = "DG"
    lineshape: str = "pseudo_voigt"
    bwf_g: bool = False
    despike_window: int = 7
    despike_z: float = 6.0
    baseline_method: str = "als"
    baseline_params: dict = field(default_factory=dict)


@dataclass
class FitResult:
    """Outcome of a pipeline fit."""

    best: dict
    cov: np.ndarray | None
    bootstrap_df: pd.DataFrame
    n_failed: int
    redchi: float
    aic: float
    bic: float
    config: PipelineConfig
    meta: dict

    def percentile_interval(self, param, lo=2.5, hi=97.5):
        """Bootstrap percentile interval for ``param`` as ``(low, high)``."""
        if param not in self.bootstrap_df.columns or self.bootstrap_df.empty:
            return (np.nan, np.nan)
        col = self.bootstrap_df[param].to_numpy()
        col = col[np.isfinite(col)]
        if col.size == 0:
            return (np.nan, np.nan)
        return (float(np.percentile(col, lo)), float(np.percentile(col, hi)))


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _estimate_noise(y):
    """Robust noise sigma from first differences (resistant to broad bands)."""
    diffs = np.diff(np.asarray(y, dtype=float))
    if diffs.size == 0:
        return 1.0
    mad = np.median(np.abs(diffs - np.median(diffs)))
    sigma = 1.4826 * mad / np.sqrt(2.0)
    if sigma == 0.0:
        sigma = np.std(y)
    return sigma if sigma > 0.0 else 1.0


def _amplitude_names(model_params):
    """Parameter names that scale linearly with intensity (area/height)."""
    return [n for n in model_params if n.endswith("_area") or n.endswith("_height")]


def _safe_fit(model, params, x, y, weights):
    """Run an lmfit fit, returning ``(result, None)`` or ``(None, message)``."""
    try:
        result = model.fit(
            y, params, x=x, weights=weights, method="least_squares"
        )
        if not np.all(np.isfinite(result.best_fit)):
            return None, "non-finite model evaluation"
        return result, None
    except Exception as exc:  # never raise out of the pipeline
        return None, repr(exc)


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def fit_spectrum(spec, config, n_boot=200, seed=None):
    """Fit ``spec`` with the configured pipeline.

    Steps: despike -> subtract baseline -> bounded weighted least squares on
    intensity rescaled to O(1) -> residual bootstrap on the fitted residuals.

    Returns a :class:`FitResult`.  Never raises on non-convergence.
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(spec.shift, dtype=float)

    # 1. Despike.
    y_ds = despike(spec.intensity, config.despike_window, config.despike_z)

    # 2. Baseline subtract.
    ds_spec = Spectrum(
        shift=x, intensity=y_ds, wavelength_nm=spec.wavelength_nm, meta=spec.meta
    )
    base, base_diag = baseline_mod.estimate(
        ds_spec, config.baseline_method, **config.baseline_params
    )
    y_corr = y_ds - base

    # Noise model and amplitude rescaling so areas/heights are O(1).
    sigma = _estimate_noise(y_corr)
    scale = float(max(np.max(np.abs(y_corr)), _TINY))
    y_s = y_corr / scale
    weights_s = np.full_like(y_s, scale / sigma)

    # 3. Build model and windowed-maxima initial guesses.
    sm = build_model(config.peak_set, config.lineshape, config.bwf_g)
    params = sm.guess(x, y_s)
    amp_names = _amplitude_names(params)

    meta = {
        "scale": scale,
        "sigma": sigma,
        "baseline": base_diag,
        "n_boot": n_boot,
    }

    result, message = _safe_fit(sm.model, params, x, y_s, weights_s)
    if result is None:
        # Record the failure rather than raising.
        best = {name: _rescale_value(name, params[name].value, scale, amp_names)
                for name in params}
        meta["success"] = False
        meta["message"] = message
        return FitResult(
            best=best,
            cov=None,
            bootstrap_df=pd.DataFrame(columns=list(params.keys())),
            # No bootstrap refit was attempted, so no bootstrap failures
            # occurred; the primary failure is recorded in meta['success'].
            n_failed=0,
            redchi=float("nan"),
            aic=float("nan"),
            bic=float("nan"),
            config=config,
            meta=meta,
        )

    meta["success"] = True
    meta["message"] = "ok"

    # Best-fit params in original intensity units.
    best = {
        name: _rescale_value(name, result.params[name].value, scale, amp_names)
        for name in result.params
    }

    # Statistics in original units.
    model_orig = result.best_fit * scale
    resid_orig = y_corr - model_orig
    n = y_corr.size
    k = int(result.nvarys)
    rss = float(np.sum(resid_orig**2))
    rss = max(rss, _TINY)
    dof = max(n - k, 1)
    redchi = float(np.sum((resid_orig / sigma) ** 2) / dof)
    aic_val = float(aic(n, k, rss))
    bic_val = float(bic(n, k, rss))

    # 4. Residual bootstrap on the fitted residuals.
    resid_s = y_s - result.best_fit
    boot_rows = []
    n_failed = 0
    for _ in range(n_boot):
        sample = rng.choice(resid_s, size=resid_s.size, replace=True)
        y_boot = result.best_fit + sample
        boot_res, _msg = _safe_fit(sm.model, result.params, x, y_boot, weights_s)
        if boot_res is None:
            n_failed += 1
            continue
        boot_rows.append(
            {
                name: _rescale_value(
                    name, boot_res.params[name].value, scale, amp_names
                )
                for name in boot_res.params
            }
        )

    bootstrap_df = pd.DataFrame(boot_rows, columns=list(result.params.keys()))

    meta["percentiles"] = {
        name: (
            (np.nan, np.nan)
            if bootstrap_df.empty
            else (
                float(np.nanpercentile(bootstrap_df[name], 2.5)),
                float(np.nanpercentile(bootstrap_df[name], 97.5)),
            )
        )
        for name in result.params
    }

    return FitResult(
        best=best,
        cov=result.covar,
        bootstrap_df=bootstrap_df,
        n_failed=n_failed,
        redchi=redchi,
        aic=aic_val,
        bic=bic_val,
        config=config,
        meta=meta,
    )


def _rescale_value(name, value, scale, amp_names):
    """Convert a fitted (scaled) parameter back to original intensity units."""
    if name in amp_names:
        return value * scale
    return value


# Re-export so callers can introspect the config dataclass fields.
def config_fields():
    """Names of the :class:`PipelineConfig` fields (convenience helper)."""
    return [f.name for f in dataclasses.fields(PipelineConfig)]


__all__ = [
    "aic",
    "bic",
    "PipelineConfig",
    "FitResult",
    "fit_spectrum",
    "config_fields",
]
