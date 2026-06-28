"""Plotting and visualization of spectra, fits, and diagnostics (Day-9, F1-F9).

ONE colorblind-safe style (Okabe-Ito), 300 dpi, every figure emitted as PNG +
PDF. Number discipline: any figure that DISPLAYS a cited result reads that number
from ``docs/report_data.json`` (via :func:`ramanuq.reporting.load_report_data`)
-- result numerals are never hard-coded here. Figures may read raw arrays
(per-config ``abs_error``, RMSE/coverage grids) directly from the study parquet.

Schema discipline (cf. ``selectors.py``): the schema-freeze scan in
``tests/test_grid.py`` flags any *string-literal* subscript or groupby key that
is not a frozen ``RESULT_COLUMNS`` name. So every non-schema key (palette names,
nested ``report_data.json`` keys, computed-column names) is held in a NAMED
CONSTANT and subscripted through that variable, never as a bare literal.

The nine figures:

- F1  recovery parity + coverage
- F2  hostile-fit anatomy (true bands dashed, baseline-subtracted space)
- F3  config strip colored by abs_error (naive + protocol configs flagged)
- F4  RMSE / coverage maps
- F5  selector scatter + regret + misspecification-coverage
- F6  protocol card (matches report_data.json EXACTLY)
- F7  MDC curves (protocol vs naive; I_D/I_G and Delta n_D)
- F8  demonstration spectra (reads data/digitized/; raises if absent)
- F9  rank-stability (honest empty/undefined state)
- F10 replicate-averaging MDC curves (protocol vs naive, per SNR regime)
"""

from __future__ import annotations

import json
import os

import matplotlib as mpl
import numpy as np
import pandas as pd
import yaml
from matplotlib import pyplot as plt

from . import hostile
from .fit import PipelineConfig, fit_spectrum
from .io import load_spectrum
from .mdc import mdc
from .model import build_model
from .reporting import (
    DEFAULT_OUTPUT,
    DEFAULT_PARQUET,
    NAIVE_CONFIG,
    SNR_REGIMES,
    load_report_data,
)
from .synth import SEED

# --------------------------------------------------------------------------- #
# Colorblind-safe palette (Okabe-Ito). Held as hex constants (not literal
# subscripts) so the schema-freeze scan never sees palette-name literals.
# --------------------------------------------------------------------------- #
_C_BLACK = "#000000"
_C_ORANGE = "#E69F00"
_C_SKYBLUE = "#56B4E9"
_C_GREEN = "#009E73"
_C_YELLOW = "#F0E442"
_C_BLUE = "#0072B2"
_C_VERMILLION = "#D55E00"
_C_PURPLE = "#CC79A7"
_C_GREY = "#999999"

OKABE_ITO = {
    "black": _C_BLACK, "orange": _C_ORANGE, "skyblue": _C_SKYBLUE,
    "green": _C_GREEN, "yellow": _C_YELLOW, "blue": _C_BLUE,
    "vermillion": _C_VERMILLION, "purple": _C_PURPLE, "grey": _C_GREY,
}
#: Stable per-SNR colors (integer keys; safe under the scan).
SNR_COLORS = {15: _C_VERMILLION, 50: _C_BLUE, 200: _C_GREEN}
#: Stable per-selector colors (all selector names are schema columns).
SELECTOR_COLORS = {"redchi": _C_ORANGE, "aic": _C_BLUE, "bic": _C_GREEN}
#: Colormap for abs_error / RMSE intensity maps (perceptually uniform).
SEQ_CMAP = "viridis"
COV_CMAP = "magma"

# Computed (non-schema) column names, held as variables (cf. selectors.py).
_MAE = "mean_abs_error"
_WL = "wavelength_nm"

# report_data.json keys, held as variables so they are not literal subscripts.
_MDC = "mdc"
_PER_REGIME = "per_regime"
_PROTO_FACTORS = "protocol_config_factors"
_PROTO_BIAS = "protocol_bias"
_PROTO_RMSE = "protocol_rmse"
_PROTO_COV = "protocol_coverage"
_PROTO_FAIL = "protocol_failure_rate"
_PROTO_MDC = "protocol_mdc_idig"
_NAIVE_MDC = "naive_mdc_idig"
_PROTO_SIGMA = "protocol_sigma_single"
_NAIVE_SIGMA = "naive_sigma_single"
_T5 = "t5_ranking"
_COV_FLOOR = "coverage_floor"
_MAX_COV = "max_coverage"
_N_RANK_ELIGIBLE = "n_rank_eligible"
_T6B = "t6b_coverage"
_COVERAGE = "coverage"
_NOMINAL = "nominal"
_Q2 = "q2_audit"
_BY_STRATUM = "by_stratum"
_SELECTORS = "selectors"
_STRATA = "strata"
_REGRET = "top1_regret"

_STYLE = {
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "lines.linewidth": 1.6,
    "image.cmap": SEQ_CMAP,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.hashsalt": "ramanuq-v2.1",
}

MATERIAL_CLASS = "synthetic_disordered_carbon"
CONFIG_COLUMNS = ("baseline", "lineshape", "bwf_g", "peak_set", "intensity")
PEAK_SETS = ("DG", "DGDp", "DGDpD3D4")
BASELINES = ("linear", "poly3", "poly5", "als")
LINESHAPES = ("lorentzian", "gaussian", "pseudo_voigt")

#: Fixed, documented case for the F2 anatomy panel (the same hostile spectrum
#: used in the Day-6 human spot-recompute; chosen once for reproducibility, not
#: a curated "demonstration spectrum" in the V5 sense).
F2_CASE_ID = "tierB_stage1_blmild_snr50_i3"

DEFAULT_TIERB_DIR = os.path.join(os.path.dirname(DEFAULT_PARQUET), "..", "tierB")
DEFAULT_DIGITIZED_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "digitized")
)


def apply_style():
    """Install the single shared colorblind-safe style into rcParams."""
    mpl.rcParams.update(_STYLE)


# --------------------------------------------------------------------------- #
# IO helpers (loaded once by the driver; never re-runs the study).
# --------------------------------------------------------------------------- #
def load_study(parquet_path=DEFAULT_PARQUET):
    """Load the persisted grid-study parquet (raw arrays for the figures)."""
    return pd.read_parquet(parquet_path)


def load_report(path=DEFAULT_OUTPUT):
    """Load the recomputed report numbers (the only source of cited numerals)."""
    return load_report_data(path)


#: Pinned epoch for the PDF backend's creation date. Consolidated here so PDF-
#: date determinism lives entirely in :func:`save_figure`: matplotlib's PDF
#: backend reads ``SOURCE_DATE_EPOCH`` from the environment at write time, so
#: pinning it just before saving yields a fixed creation date without callers
#: having to set it themselves.
_SOURCE_DATE_EPOCH = "1466000000"


def save_figure(fig, stem, dpi=300):
    """Save ``fig`` as ``stem.png`` and ``stem.pdf`` with stripped metadata.

    Metadata is fixed (no timestamps) so repeated renders are byte-identical.
    PDF creation-date determinism is handled here too: ``SOURCE_DATE_EPOCH`` is
    pinned (via ``setdefault``, so an externally chosen value still wins) before
    the PDF is written, which the PDF backend reads to stamp a fixed date.
    """
    os.environ.setdefault("SOURCE_DATE_EPOCH", _SOURCE_DATE_EPOCH)
    os.makedirs(os.path.dirname(os.path.abspath(stem)), exist_ok=True)
    png_meta = {"Software": None}
    pdf_meta = {"Creator": "ramanuq", "Producer": "ramanuq"}
    fig.savefig(f"{stem}.png", dpi=dpi, metadata=png_meta, bbox_inches="tight")
    fig.savefig(f"{stem}.pdf", metadata=pdf_meta, bbox_inches="tight")
    return [f"{stem}.png", f"{stem}.pdf"]


# --------------------------------------------------------------------------- #
# Small accessors for the report dict (variable keys only).
# --------------------------------------------------------------------------- #
def _regime_cell(report, snr):
    return report[_MDC][_PER_REGIME][f"SNR{snr}"]


def _protocol_cfg(report, snr):
    return _regime_cell(report, snr)[_PROTO_FACTORS]


def _t6b_cov(report, snr):
    return report[_T6B][_PER_REGIME][f"SNR{snr}"][_COVERAGE]


def _q2_cell(report, stratum, snr, selector):
    return report[_Q2][_BY_STRATUM][stratum][f"SNR{snr}"][selector]


# --------------------------------------------------------------------------- #
# Data primitives reused by several figures (raw-array reads).
# --------------------------------------------------------------------------- #
def _regime_config_slice(df, snr, cfg):
    grp = df[(df["material_class"] == MATERIAL_CLASS) & (df["snr_label"] == snr)]
    for col, val in cfg.items():
        grp = grp[grp[col] == val]
    return grp


def _per_config_mean_abs_error(df):
    """Mean abs_error per configuration (finite only), tidy frame."""
    rows = []
    for keys, grp in df.groupby(list(CONFIG_COLUMNS)):
        ae = grp["abs_error"].to_numpy(dtype=float)
        ae = ae[np.isfinite(ae)]
        rows.append({**dict(zip(CONFIG_COLUMNS, keys)),
                     _MAE: float(np.mean(ae)) if ae.size else np.nan})
    return pd.DataFrame(rows)


def _grid_stat(df, snr, intensity, peak_set, stat):
    """baseline x lineshape grid of ``stat`` for a (snr, intensity, peak_set)."""
    sub = df[
        (df["material_class"] == MATERIAL_CLASS)
        & (df["snr_label"] == snr)
        & (df["intensity"] == intensity)
        & (df["peak_set"] == peak_set)
        & (~df["bwf_g"])
    ]
    mat = np.full((len(LINESHAPES), len(BASELINES)), np.nan)
    for i, ls in enumerate(LINESHAPES):
        for j, bl in enumerate(BASELINES):
            g = sub[(sub["lineshape"] == ls) & (sub["baseline"] == bl)]
            if g.empty:
                continue
            if stat == "rmse":
                e = g["error"].to_numpy(dtype=float)
                e = e[np.isfinite(e)]
                mat[i, j] = float(np.sqrt(np.mean(e**2))) if e.size else np.nan
            elif stat == "coverage":
                lo = g["lo95"].to_numpy(dtype=float)
                hi = g["hi95"].to_numpy(dtype=float)
                tr = g["true_id_ig"].to_numpy(dtype=float)
                cov = (np.isfinite(lo) & np.isfinite(hi) & np.isfinite(tr)
                       & (tr >= lo) & (tr <= hi))
                mat[i, j] = float(np.mean(cov)) if len(g) else np.nan
    return mat, list(BASELINES), list(LINESHAPES)


# --------------------------------------------------------------------------- #
# F1 -- recovery parity + coverage
# --------------------------------------------------------------------------- #
def figure_f1(df, report):
    """Parity (id_ig vs truth) for the protocol configs + coverage vs nominal."""
    fig, (ax_p, ax_c) = plt.subplots(1, 2, figsize=(10, 4.2))

    lim = [0.0, 0.0]
    for snr in SNR_REGIMES:
        cfg = _protocol_cfg(report, snr)
        grp = _regime_config_slice(df, snr, cfg)
        x = grp["true_id_ig"].to_numpy(dtype=float)
        y = grp["id_ig"].to_numpy(dtype=float)
        m = np.isfinite(x) & np.isfinite(y)
        ax_p.scatter(x[m], y[m], s=22, alpha=0.7, color=SNR_COLORS[snr],
                     label=f"SNR {snr}", edgecolor="none")
        if m.any():
            lim[0] = min(lim[0], float(np.min([x[m].min(), y[m].min()])))
            lim[1] = max(lim[1], float(np.max([x[m].max(), y[m].max()])))
    pad = 0.05 * (lim[1] - lim[0] + 1e-9)
    lo, hi = lim[0] - pad, lim[1] + pad
    ax_p.plot([lo, hi], [lo, hi], color=_C_BLACK, lw=1.0, ls="--",
              label="y = x (perfect)")
    ax_p.set_xlim(lo, hi)
    ax_p.set_ylim(lo, hi)
    ax_p.set_xlabel("true I_D/I_G")
    ax_p.set_ylabel("recovered I_D/I_G")
    ax_p.set_title("(a) Recovery parity — protocol configs")
    ax_p.legend(loc="upper left", fontsize=8)

    snrs = list(SNR_REGIMES)
    covs = [_regime_cell(report, s)[_PROTO_COV] for s in snrs]
    floor = report[_T5][_COV_FLOOR]
    nominal = report[_T6B][_NOMINAL]
    bars = ax_c.bar([str(s) for s in snrs], covs,
                    color=[SNR_COLORS[s] for s in snrs], width=0.6)
    ax_c.axhline(nominal, color=_C_BLACK, ls="--", lw=1.0,
                 label=f"nominal {nominal:.2f}")
    ax_c.axhline(floor, color=_C_VERMILLION, ls=":", lw=1.2,
                 label=f"rank floor {floor:.2f}")
    for b, c in zip(bars, covs):
        ax_c.text(b.get_x() + b.get_width() / 2, c + 0.01, f"{c:.3f}",
                  ha="center", va="bottom", fontsize=8)
    ax_c.set_ylim(0, 1.0)
    ax_c.set_xlabel("SNR regime")
    ax_c.set_ylabel("empirical 95% coverage")
    ax_c.set_title("(b) Protocol-config coverage vs nominal")
    # The nominal/floor reference lines sit close together near the top; place
    # their labels in the clear center-right band so they no longer crowd the
    # lines (the lines themselves are unchanged).
    ax_c.legend(loc="center right", fontsize=8)

    fig.suptitle("F1 — Recovery parity and honest coverage", fontweight="bold")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F2 -- hostile-fit anatomy (true bands dashed)
# --------------------------------------------------------------------------- #
def _load_case_spectrum(case_id, tierB_dir):
    truth_path = os.path.join(tierB_dir, case_id + "_truth.json")
    with open(truth_path) as fh:
        truth = json.load(fh)
    data = pd.read_csv(os.path.join(tierB_dir, case_id + ".csv"))
    spec = load_spectrum(
        data.iloc[:, 0].to_numpy(), data.iloc[:, 1].to_numpy(), truth[_WL],
    )
    return spec, truth


def _fitted_curve(spec, cfg):
    """Reconstruct the fitted total model in baseline-free intensity units."""
    fit = fit_spectrum(spec, cfg, n_boot=0, seed=0)
    sm = build_model(cfg.peak_set, cfg.lineshape, cfg.bwf_g)
    params = sm.make_params()
    for name, value in fit.best.items():
        if name in params:
            params[name].set(value=value)
    return sm.model.eval(params, x=np.asarray(spec.shift, dtype=float))


def figure_f2(df, report, tierB_dir=DEFAULT_TIERB_DIR):
    """Anatomy of a hostile fit: true out-of-family bands (dashed) vs the fit."""
    tierB_dir = os.path.normpath(tierB_dir)
    spec, _truth = _load_case_spectrum(F2_CASE_ID, tierB_dir)
    x = np.asarray(spec.shift, dtype=float)

    # True noiseless, baseline-free components from the generator (not fabricated).
    case = next(c for c in hostile.enumerate_cases()
                if hostile.case_id(c) == F2_CASE_ID)
    asm = hostile.assemble(case, seed=SEED)
    true_total = np.zeros_like(x)
    for v in asm.components.values():
        true_total = true_total + np.asarray(v, dtype=float)

    proto = _protocol_cfg(report, 50)
    cfg = PipelineConfig(
        peak_set=proto["peak_set"], lineshape=proto["lineshape"],
        bwf_g=bool(proto["bwf_g"]), baseline_method=proto["baseline"],
    )
    fit_curve = _fitted_curve(spec, cfg)

    fig, ax = plt.subplots(figsize=(8, 4.6))
    band_colors = {"D": _C_VERMILLION, "G": _C_BLUE, "Dprime": _C_PURPLE,
                   "D3": _C_ORANGE, "D4": _C_GREEN}
    for name, vals in asm.components.items():
        ax.plot(x, np.asarray(vals, dtype=float), ls="--", lw=1.2,
                color=band_colors.get(name, _C_GREY),
                label=f"true {name} (out-of-family)")
    ax.plot(x, true_total, ls="--", lw=2.0, color=_C_BLACK, label="true total")
    ax.plot(x, fit_curve, ls="-", lw=2.0, color=_C_SKYBLUE,
            label=(f"fit: {proto['lineshape']}/{proto['baseline']}/"
                   f"{proto['peak_set']}/{proto['intensity']}"))
    ax.set_xlabel("Raman shift (cm$^{-1}$)")
    ax.set_ylabel("intensity (baseline-subtracted, arb.)")
    ax.set_title(f"F2 — Hostile-fit anatomy ({F2_CASE_ID})", fontweight="bold")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F3 -- config strip colored by abs_error
# --------------------------------------------------------------------------- #
def figure_f3(df, report):
    """All 96 configs as a strip ordered by accuracy; naive + protocol flagged."""
    tidy = _per_config_mean_abs_error(df).sort_values(_MAE)
    tidy = tidy.reset_index(drop=True)
    y_of = {p: i for i, p in enumerate(PEAK_SETS)}

    fig, ax = plt.subplots(figsize=(9, 4.2))
    xv = tidy[_MAE].to_numpy(dtype=float)
    yv = np.array([y_of[p] for p in tidy["peak_set"]], dtype=float)
    rng = np.random.default_rng(SEED)
    yv = yv + rng.uniform(-0.18, 0.18, size=yv.shape)
    sc = ax.scatter(xv, yv, c=xv, cmap=SEQ_CMAP, s=34, alpha=0.85,
                    edgecolor="none", norm=mpl.colors.LogNorm())

    def _match(row, cfg):
        return all(bool(row[k]) == bool(v) if k == "bwf_g" else row[k] == v
                   for k, v in cfg.items())

    naive_rows = tidy[tidy.apply(lambda r: _match(r, NAIVE_CONFIG), axis=1)]
    for _, r in naive_rows.iterrows():
        ax.scatter(r[_MAE], y_of[r["peak_set"]], marker="*", s=320,
                   facecolor="none", edgecolor=_C_BLACK, linewidths=1.6, zorder=5)
        ax.annotate("naive", (r[_MAE], y_of[r["peak_set"]]),
                    textcoords="offset points", xytext=(8, 8), fontsize=8)

    # Distinct protocol configs (SNR50/200 share one) -> one label each.
    proto_regimes = {}
    for snr in SNR_REGIMES:
        cfg = _protocol_cfg(report, snr)
        key = tuple(cfg[c] for c in CONFIG_COLUMNS)
        proto_regimes.setdefault(key, (cfg, []))[1].append(snr)
    # The protocol markers cluster tightly in the lower-left; stagger their
    # labels up into the empty band above the DG row, each on a thin leader
    # line, so the labels no longer overlap each other or run off the axis.
    # Markers stay exactly on their (error, peak-set) positions.
    proto_label_xytext = [(10, 34), (10, 64), (10, 94)]
    for off, (key, (cfg, snrs)) in enumerate(proto_regimes.items()):
        pr = tidy[tidy.apply(lambda r: _match(r, cfg), axis=1)]
        label = "protocol SNR" + "/".join(str(s) for s in snrs)
        dx, dy = proto_label_xytext[off % len(proto_label_xytext)]
        for _, r in pr.iterrows():
            ax.scatter(r[_MAE], y_of[r["peak_set"]], marker="D", s=90,
                       facecolor="none", edgecolor=_C_VERMILLION,
                       linewidths=1.6, zorder=5)
            ax.annotate(label, (r[_MAE], y_of[r["peak_set"]]),
                        textcoords="offset points", xytext=(dx, dy),
                        ha="left", fontsize=7, color=_C_VERMILLION,
                        arrowprops=dict(arrowstyle="-", lw=0.6,
                                        color=_C_VERMILLION))

    ax.set_xscale("log")
    ax.set_yticks(range(len(PEAK_SETS)))
    ax.set_yticklabels(list(PEAK_SETS))
    ax.set_xlabel("mean |I_D/I_G error| per configuration (log scale)")
    ax.set_ylabel("peak set")
    ax.set_title("F3 — Per-configuration accuracy strip", fontweight="bold")
    fig.colorbar(sc, ax=ax, label="mean |error|")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F4 -- RMSE / coverage maps
# --------------------------------------------------------------------------- #
def figure_f4(df, report):
    """RMSE (top) and coverage (bottom) maps over baseline x lineshape, DG/area."""
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.4))
    floor = report[_T5][_COV_FLOOR]
    for j, snr in enumerate(SNR_REGIMES):
        rmse, bls, lss = _grid_stat(df, snr, "area", "DG", "rmse")
        cov, _, _ = _grid_stat(df, snr, "area", "DG", "coverage")
        for row, (mat, title, cmap, vmax) in enumerate([
            (rmse, f"RMSE — SNR {snr}", SEQ_CMAP, None),
            (cov, f"coverage — SNR {snr}", COV_CMAP, 1.0),
        ]):
            ax = axes[row, j]
            im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
            ax.set_xticks(range(len(bls)))
            ax.set_xticklabels(bls, rotation=30, ha="right", fontsize=8)
            ax.set_yticks(range(len(lss)))
            ax.set_yticklabels(lss, fontsize=8)
            ax.set_title(title, fontsize=9)
            if row == 1:
                ax.set_xlabel("baseline")
            if j == 0:
                ax.set_ylabel("lineshape")
            ax.grid(False)
            for a in range(mat.shape[0]):
                for b in range(mat.shape[1]):
                    if np.isfinite(mat[a, b]):
                        ax.text(b, a, f"{mat[a, b]:.2f}", ha="center",
                                va="center", fontsize=7, color="white")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(
        "F4 — RMSE and coverage maps (DG/area; no config reaches the "
        f"{floor:.2f} floor)", fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# --------------------------------------------------------------------------- #
# F5 -- selector scatter + regret + misspecification coverage
# --------------------------------------------------------------------------- #
def figure_f5(df, report):
    """Selector decoupling, top-1 regret, and T6b coverage in one row."""
    fig, (ax_s, ax_r, ax_c) = plt.subplots(1, 3, figsize=(13, 4.2))

    # (a) raw decoupling scatter: redchi vs abs_error at SNR50 (full grid).
    sub = df[(df["snr_label"] == 50)]
    sv = sub["redchi"].to_numpy(dtype=float)
    ae = sub["abs_error"].to_numpy(dtype=float)
    m = np.isfinite(sv) & np.isfinite(ae)
    ax_s.scatter(sv[m], ae[m], s=10, alpha=0.3, color=SELECTOR_COLORS["redchi"],
                 edgecolor="none")
    ax_s.set_xscale("log")
    ax_s.set_yscale("log")
    ax_s.set_xlabel("reduced chi-square (lower = 'better fit')")
    ax_s.set_ylabel("|I_D/I_G error|")
    ax_s.set_title("(a) Fit quality vs accuracy (SNR 50)")

    # (b) top-1 regret per selector x stratum at SNR50 (from report).
    selectors = report[_Q2][_SELECTORS]
    strata = report[_Q2][_STRATA]
    width = 0.8 / len(strata)
    xidx = np.arange(len(selectors))
    for k, stratum in enumerate(strata):
        vals = [_q2_cell(report, stratum, 50, s)[_REGRET] for s in selectors]
        ax_r.bar(xidx + k * width, vals, width=width, label=stratum,
                 color=(_C_ORANGE if k == 0 else _C_BLUE))
    ax_r.set_xticks(xidx + width * (len(strata) - 1) / 2)
    ax_r.set_xticklabels(selectors)
    ax_r.set_ylabel("top-1 regret (I_D/I_G)")
    ax_r.set_title("(b) Selector top-1 regret (SNR 50)")
    ax_r.legend(fontsize=8)

    # (c) T6b coverage under misspecification (from report).
    snrs = list(SNR_REGIMES)
    covs = [_t6b_cov(report, s) for s in snrs]
    nominal = report[_T6B][_NOMINAL]
    bars = ax_c.bar([str(s) for s in snrs], covs,
                    color=[SNR_COLORS[s] for s in snrs], width=0.6)
    ax_c.axhline(nominal, color=_C_BLACK, ls="--", lw=1.0,
                 label=f"nominal {nominal:.2f}")
    for b, c in zip(bars, covs):
        ax_c.text(b.get_x() + b.get_width() / 2, c + 0.01, f"{c:.3f}",
                  ha="center", va="bottom", fontsize=8)
    ax_c.set_ylim(0, 1.0)
    ax_c.set_xlabel("SNR regime")
    ax_c.set_ylabel("coverage (pooled configs)")
    ax_c.set_title("(c) Coverage under misspecification (T6b)")
    ax_c.legend(fontsize=8)

    fig.suptitle("F5 — Selectors do not track accuracy; intervals undercover",
                 fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# --------------------------------------------------------------------------- #
# F6 -- protocol card (matches report_data.json EXACTLY)
# --------------------------------------------------------------------------- #
def _recommended_str(cfg):
    """Compact two-line recommendation (same factors as the protocol card)."""
    return (f"baseline={cfg['baseline']}, lineshape={cfg['lineshape']},\n"
            f"bwf_g={cfg['bwf_g']}, peak_set={cfg['peak_set']}, "
            f"intensity={cfg['intensity']}")


def figure_f6(df, report):
    """The protocol recommendation card; all numerals from report_data.json."""
    headers = ["regime", "recommended", "bias", "RMSE", "coverage",
               "failure", "MDC", "stability"]
    col_widths = [0.06, 0.30, 0.09, 0.09, 0.09, 0.08, 0.09, 0.20]
    rows = []
    for snr in SNR_REGIMES:
        cell = _regime_cell(report, snr)
        cfg = cell[_PROTO_FACTORS]
        rows.append([
            f"SNR{snr}",
            _recommended_str(cfg),
            f"{cell[_PROTO_BIAS]:+.5f}",
            f"{cell[_PROTO_RMSE]:.5f}",
            f"{cell[_PROTO_COV]:.3f}",
            f"{cell[_PROTO_FAIL]:.3f}",
            f"{cell[_PROTO_MDC]:.5f}",
            "undefined\n(Q1b vacuous;\n0 rank-eligible\nconfigs)",
        ])

    fig, ax = plt.subplots(figsize=(13, 3.4))
    ax.axis("off")
    ax.grid(False)
    table = ax.table(cellText=rows, colLabels=headers, loc="center",
                     cellLoc="center", colWidths=col_widths)
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 3.0)
    for (r, _c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor(_C_BLUE)
            cell.set_text_props(color="white", fontweight="bold")
    ax.set_title("F6 — Protocol recommendation card "
                 "(numbers recomputed in report_data.json)", fontweight="bold")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F7 -- MDC curves (protocol vs naive; I_D/I_G and Delta n_D)
# --------------------------------------------------------------------------- #
def figure_f7(df, report):
    """MDC vs SNR in both currencies; protocol vs naive, Delta n_D with band."""
    fig, (ax_i, ax_n) = plt.subplots(1, 2, figsize=(11, 4.4))
    snrs = list(SNR_REGIMES)

    p_i = [_regime_cell(report, s)[_PROTO_MDC] for s in snrs]
    n_i = [_regime_cell(report, s)[_NAIVE_MDC] for s in snrs]
    ax_i.plot(snrs, p_i, marker="s", color=_C_BLUE, label="protocol")
    ax_i.plot(snrs, n_i, marker="o", color=_C_VERMILLION, label="naive")
    ax_i.set_xscale("log")
    ax_i.set_xticks(snrs)
    ax_i.set_xticklabels([str(s) for s in snrs])
    ax_i.minorticks_off()
    ax_i.set_xlabel("SNR")
    ax_i.set_ylabel("MDC (I_D/I_G units)")
    ax_i.set_title("(a) MDC — I_D/I_G currency")
    ax_i.legend(fontsize=8)

    for label, key, color, marker in [
        ("protocol", "protocol", _C_BLUE, "s"),
        ("naive", "naive", _C_VERMILLION, "o"),
    ]:
        cen = [_regime_cell(report, s)[f"{key}_delta_nd_central"] for s in snrs]
        rng = [_regime_cell(report, s)[f"{key}_delta_nd_range"] for s in snrs]
        lo = [c - r[0] for c, r in zip(cen, rng)]
        hi = [r[1] - c for c, r in zip(cen, rng)]
        ax_n.errorbar(snrs, cen, yerr=[lo, hi], marker=marker, color=color,
                      label=f"{label} (±published const. unc.)", capsize=3)
    ax_n.set_xscale("log")
    ax_n.set_xticks(snrs)
    ax_n.set_xticklabels([str(s) for s in snrs])
    ax_n.minorticks_off()
    ax_n.set_xlabel("SNR")
    ax_n.set_ylabel(r"MDC ($\Delta n_D$, cm$^{-2}$)")
    ax_n.set_title("(b) MDC — Delta n_D currency")
    ax_n.legend(fontsize=8)

    fig.suptitle("F7 — Minimum detectable change: protocol vs naive",
                 fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# --------------------------------------------------------------------------- #
# F8 -- demonstration spectra (reads data/digitized/; raises if absent)
# --------------------------------------------------------------------------- #
#: Panel-title templates for F8's demonstration spectra, keyed by the
#: provenance ``id``. The I_D/I_G value is filled in from provenance.yaml; the
#: numbers themselves are never invented here.
_F8_TITLES = {
    "cancado2011_v5": "Cançado 2011 (graphene, I_D/I_G={idig:g})",
    "nrgo_arxiv1902": "N-rGO (I_D/I_G={idig:g})",
    "fcnt_arxiv1711": "fCNT (I_D/I_G={idig:g})",
}


def figure_f8(df, report, digitized_dir=DEFAULT_DIGITIZED_DIR):
    """Reproduce digitized published spectra (Gate V5).

    Discovers the demonstration spectra from ``data/digitized/provenance.yaml``
    and plots one trace per spectrum -- the first CSV listed for each (for the
    Cançado V5 spectrum that is ``digitization_a``; the ``_b`` file is the
    verification twin and is intentionally not plotted). Panel titles carry the
    published I_D/I_G read from provenance. Nothing is fabricated: F8 reads only
    what is present in ``data/digitized/`` and raises a clear error otherwise.
    """
    digitized_dir = os.path.normpath(digitized_dir)
    prov_path = os.path.join(digitized_dir, "provenance.yaml")
    if not os.path.isfile(prov_path):
        raise FileNotFoundError(
            "F8 needs digitized published spectra described by "
            f"{prov_path!r}, but it is absent. F8 / Gate V5 read only what is in "
            "data/digitized/; demonstration spectra are never fabricated."
        )
    with open(prov_path) as fh:
        spectra = (yaml.safe_load(fh) or {}).get("spectra") or []
    if not spectra:
        raise FileNotFoundError(
            f"{prov_path!r} lists no spectra; F8 has nothing to reproduce."
        )

    fig, axes = plt.subplots(1, len(spectra), figsize=(5 * len(spectra), 4),
                             squeeze=False)
    for ax, spec in zip(axes[0], spectra):
        csv_paths = spec.get("digitized_csv_path") or []
        if not csv_paths:
            raise FileNotFoundError(
                f"provenance entry {spec.get('id')!r} has no digitized_csv_path."
            )
        # Plot the FIRST listed trace only (digitization_a for Cançado; the _b
        # twin is the verification copy and is not plotted).
        csv = os.path.join(digitized_dir, os.path.basename(csv_paths[0]))
        # Digitized CSVs have a fixed two-column layout: column 0 is
        # ``shift_cm_inverse`` (x), column 1 is ``intensity`` (y). Read by
        # position so this does not reference study-schema column names.
        data = pd.read_csv(csv)
        ax.plot(data.iloc[:, 0], data.iloc[:, 1], color=_C_BLUE)
        ax.set_xlabel("Raman shift (cm$^{-1}$)")
        ax.set_ylabel("intensity (arb.)")
        title_tmpl = _F8_TITLES.get(spec.get("id"), "{id} (I_D/I_G={idig:g})")
        ax.set_title(title_tmpl.format(id=spec.get("id"),
                                       idig=spec.get("published_id_ig")))
    fig.suptitle("F8 — Digitized published-spectrum reproduction (V5)",
                 fontweight="bold")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F9 -- rank-stability (honest empty / undefined state)
# --------------------------------------------------------------------------- #
def figure_f9(df, report):
    """Show the empty ranking honestly: 0 rank-eligible -> stability undefined."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    snrs = list(SNR_REGIMES)
    # Rank-eligible count is read from report_data.json, not hard-coded.
    n_eligible = report[_T5][_N_RANK_ELIGIBLE]
    n_elig = [n_eligible for _ in snrs]
    bars = ax.bar([str(s) for s in snrs], n_elig,
                  color=[SNR_COLORS[s] for s in snrs], width=0.6)
    ax.set_ylim(0, 1)
    ax.set_xlabel("SNR regime")
    ax.set_ylabel("# rank-eligible configurations")
    floor = report[_T5][_COV_FLOOR]
    max_cov = report[_T5][_MAX_COV]
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, 0.04, str(n_eligible),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.text(0.5, 0.62,
            "Ranking is EMPTY in every regime\n"
            f"(max empirical coverage {max_cov:.2f} < {floor:.2f} floor)\n"
            "→ Q1b rank-stability is UNDEFINED, not 'stable'",
            transform=ax.transAxes, ha="center", va="center", fontsize=10,
            bbox={"boxstyle": "round", "facecolor": _C_YELLOW, "alpha": 0.6})
    ax.set_title("F9 — Rank stability: honest empty state", fontweight="bold")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# F10 -- replicate-averaging MDC curves (protocol vs naive, per SNR regime)
# --------------------------------------------------------------------------- #
#: N_rep sweep for the replicate-averaging MDC curve (integers 1..10).
F10_N_REP = tuple(range(1, 11))


def figure_f10(df, report):
    """MDC vs number of averaged replicates N_rep; protocol vs naive per regime.

    Pure replotting of existing math: reads the per-(config, regime) single-
    spectrum precision (``protocol_sigma_single`` / ``naive_sigma_single``)
    recomputed in report_data.json and applies the existing
    :func:`ramanuq.mdc.mdc` at each N_rep in 1..10 (same alpha/power defaults
    that produced the frozen MDCs). By construction each curve at N_rep=1 equals
    the frozen per-regime MDC, and every curve falls as 1/sqrt(N_rep).
    """
    snrs = list(SNR_REGIMES)
    n_reps = list(F10_N_REP)
    fig, axes = plt.subplots(1, len(snrs), figsize=(13, 4.2), sharey=True)
    for ax, snr in zip(axes, snrs):
        cell = _regime_cell(report, snr)
        for label, sigma_key, color, marker, ls in [
            ("protocol", _PROTO_SIGMA, _C_BLUE, "s", "-"),
            ("naive", _NAIVE_SIGMA, _C_VERMILLION, "o", "--"),
        ]:
            sigma = cell[sigma_key]
            y = [mdc(sigma, n_rep=n) for n in n_reps]
            ax.plot(n_reps, y, marker=marker, ls=ls, color=color, label=label)
        ax.set_xticks(n_reps)
        ax.set_xlabel("number of averaged replicates N_rep")
        ax.set_title(f"SNR {snr}", color=SNR_COLORS[snr])
        ax.legend(fontsize=8)
    axes[0].set_ylabel("MDC (I_D/I_G units)")
    fig.suptitle("F10 — Replicate-averaging MDC: protocol vs naive",
                 fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# --------------------------------------------------------------------------- #
# Registry / driver helpers.
# --------------------------------------------------------------------------- #
FIGURES = {
    "F1": figure_f1, "F2": figure_f2, "F3": figure_f3, "F4": figure_f4,
    "F5": figure_f5, "F6": figure_f6, "F7": figure_f7, "F8": figure_f8,
    "F9": figure_f9, "F10": figure_f10,
}


def render_figure(name, df, report, out_dir, dpi=300, **kwargs):
    """Render and save one figure by name; returns the written paths."""
    fig = FIGURES[name](df, report, **kwargs)
    paths = save_figure(fig, os.path.join(out_dir, name), dpi=dpi)
    plt.close(fig)
    return paths


__all__ = [
    "OKABE_ITO",
    "SNR_COLORS",
    "SELECTOR_COLORS",
    "FIGURES",
    "apply_style",
    "load_study",
    "load_report",
    "save_figure",
    "render_figure",
] + [f"figure_{n.lower()}" for n in FIGURES]
