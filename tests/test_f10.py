"""Tests for the F10 replicate-averaging MDC curve (viz + report_data.json).

F10 is pure replotting of existing math: the per-(config, regime) sigma_single
recomputed in report_data.json, fed through the existing ``mdc()`` swept over
N_rep 1..10. These tests pin three properties:

(a) at N_rep=1 every curve equals the frozen per-regime MDC
    (protocol 0.529/0.271/0.565, naive 0.745/0.763/0.703 for SNR 15/50/200);
(b) each curve falls as 1/sqrt(N_rep) (N_rep=4 -> half of N_rep=1);
(c) report_data.json carries f10_replicate_mdc with 10 N_rep points per
    regime/config.
"""

import json
import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from ramanuq import viz  # noqa: E402
from ramanuq.reporting import DEFAULT_OUTPUT, SNR_REGIMES  # noqa: E402

# Frozen per-regime, single-spectrum (N_rep=1) MDCs (protocol.md / report_data).
FROZEN_PROTOCOL_MDC = {15: 0.529, 50: 0.271, 200: 0.565}
FROZEN_NAIVE_MDC = {15: 0.745, 50: 0.763, 200: 0.703}


def _f10_curves():
    """Return {(snr, label): ydata} for the two curves of each F10 subplot."""
    df = viz.load_study()
    report = viz.load_report()
    fig = viz.figure_f10(df, report)
    curves = {}
    for ax in fig.axes:
        title = ax.get_title()  # e.g. "SNR 15"
        if not title.startswith("SNR "):
            continue
        snr = int(title.split()[-1])
        for line in ax.get_lines():
            label = line.get_label()
            if label in ("protocol", "naive"):
                curves[(snr, label)] = list(line.get_ydata())
    plt.close(fig)
    return curves


def test_f10_nrep1_matches_frozen_mdc():
    """(a) N_rep=1 point of each curve == the frozen per-regime MDC (3 dp)."""
    curves = _f10_curves()
    for snr in SNR_REGIMES:
        assert round(curves[(snr, "protocol")][0], 3) == FROZEN_PROTOCOL_MDC[snr]
        assert round(curves[(snr, "naive")][0], 3) == FROZEN_NAIVE_MDC[snr]


def test_f10_scales_as_inverse_sqrt_nrep():
    """(b) MDC at N_rep=4 is exactly half of MDC at N_rep=1 (sqrt(4) == 2)."""
    curves = _f10_curves()
    for snr in SNR_REGIMES:
        for label in ("protocol", "naive"):
            y = curves[(snr, label)]
            assert len(y) == 10
            assert math.isclose(y[3], y[0] / 2.0, rel_tol=1e-12)


def test_report_data_has_f10_replicate_mdc():
    """(c) report_data.json carries f10_replicate_mdc, 10 points per regime/config."""
    with open(DEFAULT_OUTPUT) as fh:
        report = json.load(fh)
    f10 = report["f10_replicate_mdc"]
    assert f10["n_rep_values"] == list(range(1, 11))
    for snr in SNR_REGIMES:
        cell = f10["per_regime"][f"SNR{snr}"]
        assert len(cell["protocol_mdc_idig"]) == 10
        assert len(cell["naive_mdc_idig"]) == 10
        # The stored N_rep=1 entry reproduces the frozen per-regime MDC.
        assert round(cell["protocol_mdc_idig"][0], 3) == FROZEN_PROTOCOL_MDC[snr]
        assert round(cell["naive_mdc_idig"][0], 3) == FROZEN_NAIVE_MDC[snr]
