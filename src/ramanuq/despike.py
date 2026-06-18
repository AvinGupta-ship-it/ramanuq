"""Detection and removal of cosmic-ray spikes from spectra.

The despiker compares each channel against a rolling median and flags points
whose robust (MAD-based) z-score exceeds a threshold.  Flagged points are
replaced by the local median.  Because real Raman bands are broad relative to
the rolling window, their monotonic flanks have near-zero median residuals and
survive, while single-channel spikes are removed.  Replacing spikes with the
local median makes the operation idempotent: a second pass finds nothing.
"""

from __future__ import annotations

import numpy as np

_MAD_TO_SIGMA = 1.4826  # scale factor: robust sigma = 1.4826 * MAD (normal data)


def _rolling_median(y, window):
    """Edge-padded rolling median with an odd window length."""
    if window % 2 == 0:
        window += 1
    half = window // 2
    padded = np.pad(y, half, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)
    return np.median(windows, axis=1)


def despike(intensity, window=7, z_thresh=6.0):
    """Remove spikes from ``intensity`` using a rolling-median z-score.

    Parameters
    ----------
    intensity:
        1-D intensity array.
    window:
        Rolling-median window length (forced odd).
    z_thresh:
        Robust z-score above which a channel is treated as a spike.

    Returns
    -------
    numpy.ndarray
        A new array with spikes replaced by the local median.  Idempotent:
        ``despike(despike(y)) == despike(y)``.
    """
    y = np.asarray(intensity, dtype=float).copy()
    if y.size == 0:
        return y

    med = _rolling_median(y, window)
    resid = y - med

    mad = np.median(np.abs(resid - np.median(resid)))
    sigma = _MAD_TO_SIGMA * mad
    if sigma == 0.0:
        sigma = np.std(resid)
    if sigma == 0.0:
        # Nothing varies; there is no spike to detect.
        return y

    z = np.abs(resid) / sigma
    spikes = z > z_thresh
    y[spikes] = med[spikes]
    return y
