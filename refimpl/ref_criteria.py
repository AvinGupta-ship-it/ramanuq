"""Reference information criteria for least-squares fits.

With n data points, k fitted parameters, RSS = residual sum of squares, and
log = natural logarithm:

    AIC = n*log(RSS/n) + 2*k
    BIC = n*log(RSS/n) + k*log(n)
"""

import numpy as np


def aic(n, k, rss):
    """Akaike information criterion: n*log(RSS/n) + 2*k."""
    return n * np.log(rss / n) + 2.0 * k


def bic(n, k, rss):
    """Bayesian information criterion: n*log(RSS/n) + k*log(n)."""
    return n * np.log(rss / n) + k * np.log(n)
