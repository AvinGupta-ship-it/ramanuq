import numpy as np
from scipy.stats import norm


def ref_mdc(sigma_single, alpha=0.05, power=0.8, n_rep=1):
    """Minimum Detectable Change in I_D/I_G.
    MDC = (z_{1 - alpha/2} + z_{power}) * sqrt(2) * sigma_single / sqrt(n_rep),
    where z_q is the q-quantile of the standard normal distribution
    (use scipy.stats.norm.ppf). sqrt(2) arises because the change is a
    difference of two independent measurements. Return a float."""
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    return float((z_alpha + z_power) * np.sqrt(2) * sigma_single / np.sqrt(n_rep))


def ref_to_delta_nd(mdc_value, c_central, c_lo, c_hi):
    """Propagate an MDC in I_D/I_G to a defect-density change Delta n_D using a
    multiplicative calibration: n_D = C * (I_D/I_G), so Delta n_D = C * mdc_value.
    The calibration constant C carries published uncertainty given here as the
    triple (c_central, c_lo, c_hi). Return the tuple
    (c_central * mdc_value, c_lo * mdc_value, c_hi * mdc_value)."""
    return (c_central * mdc_value, c_lo * mdc_value, c_hi * mdc_value)
