"""Clean-room reference implementation of selector scoring.

Implements ConfigScore and score_configs from a mathematical specification.
The selector is LOWER-IS-BETTER (smaller selector value => predicted better config).
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata


@dataclass(frozen=True)
class ConfigScore:
    rho: float
    top1_regret: float
    top_quartile_hit: float
    n: int


def score_configs(selector_values, abs_errors) -> ConfigScore:
    sel = np.asarray(selector_values, dtype=float)
    err = np.asarray(abs_errors, dtype=float)
    n = int(sel.shape[0])

    if n == 0:
        return ConfigScore(float("nan"), float("nan"), float("nan"), 0)

    # Spearman rank correlation with average-rank tie handling.
    if n < 2:
        rho = float("nan")
    else:
        sel_ranks = rankdata(sel, method="average")
        err_ranks = rankdata(err, method="average")
        # A constant input has no rank variation -> correlation undefined.
        if np.ptp(sel_ranks) == 0 or np.ptp(err_ranks) == 0:
            rho = float("nan")
        else:
            rho = float(np.corrcoef(sel_ranks, err_ranks)[0, 1])

    # Selector's top pick: first occurrence of the minimum selector value.
    i = int(np.argmin(sel))

    # Regret of the top pick vs the oracle (best achievable error).
    oracle = float(np.min(err))
    top1_regret = float(err[i] - oracle)

    # Whether the top pick lands in the best quartile of errors.
    threshold = float(np.percentile(err, 25))
    top_quartile_hit = 1.0 if err[i] <= threshold else 0.0

    return ConfigScore(rho, top1_regret, top_quartile_hit, n)


if __name__ == "__main__":
    # (1) Perfectly rank-aligned: selector order matches error order.
    aligned = score_configs([1, 2, 3, 4], [0.1, 0.2, 0.3, 0.4])
    print("aligned:", aligned)

    # (2) Perfectly rank-reversed: lowest selector picks the worst config.
    reversed_ = score_configs([1, 2, 3, 4], [0.4, 0.3, 0.2, 0.1])
    print("reversed:", reversed_)

    assert abs(aligned.rho - 1.0) < 1e-9, aligned.rho
    assert abs(aligned.top1_regret - 0.0) < 1e-9, aligned.top1_regret

    assert abs(reversed_.rho - (-1.0)) < 1e-9, reversed_.rho
    assert abs(reversed_.top1_regret - 0.3) < 1e-9, reversed_.top1_regret

    print("self-check passed")
