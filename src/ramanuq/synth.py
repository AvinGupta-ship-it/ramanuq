"""Generation of synthetic Raman spectra for testing and validation (Tier A).

Tier A is the *in-family* synthetic suite: every band is rendered with one of the
two families the fitter can represent analytically, Lorentzian or Gaussian (no
Tier-B shapes).  Spectra are built directly from the area-parameterized line
shapes in :mod:`ramanuq.lineshapes`, so the ground truth is the *analytic*
band area (the ``area`` parameter, which is the infinite-axis integral) and the
*analytic* band height (the line shape's maximum).  Truth is never read back off
the (possibly noisy / baselined) generated curve.

Determinism is anchored to a single project seed, :data:`SEED`.  All randomness
(noise, optional cosmic spikes) derives from a :class:`numpy.random.SeedSequence`
mixing ``SEED`` with a stable per-case key, so the same seed reproduces every
spectrum and every truth record bit-for-bit.

Operational ground-truth definition (pre-registered, validation_plan.md S2):
true area is the integral of the band function; true height is its maximum.
Both are stored per spectrum, under the labelled keys ``true_id_ig_area`` and
``true_id_ig_height`` (contracts.md carries no overriding frozen key names).
"""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import lineshapes
from .io import Spectrum, load_spectrum

# --------------------------------------------------------------------------- #
# Project-wide deterministic seed and Tier-A generator constants
# --------------------------------------------------------------------------- #
#: Single project seed (the pre-registration freeze date, 2026-06-15).  Every
#: stochastic Tier-A draw is reproducible from this constant.
SEED = 20260615

#: Excitation wavelength stored on each Spectrum (nm).  Within-spectrum I_D/I_G
#: comparisons are wavelength-independent (assumptions.md A5); this only feeds
#: the Spectrum container's positivity contract.
WAVELENGTH_NM = 532.0

#: Reference G-band area; absolute scale is irrelevant to the (ratio) truth but
#: keeps peak heights at O(10) for readable plots.
G_AREA_BASE = 1000.0

#: Grids (min, max, step) in cm^-1.  Cases without D4 use the narrow grid;
#: cases with D4 (stage 2) use the wide grid so the broad D4 band is captured.
GRID_NO_D4 = (1000.0, 1800.0, 1.0)
GRID_WITH_D4 = (800.0, 1900.0, 1.0)

#: Stage-1 true I_D/I_G *area* ratios (swept).  Stage 2 is a single fixed
#: configuration at area ratio 1.0.
STAGE1_RATIOS = (0.1, 0.5, 1.0, 2.0)
STAGE2_RATIO = 1.0

BASELINE_LABELS = ("none", "mild_cubic", "strong_curved")
SNR_LEVELS = (200, 50, 15)

_BASELINE_TAG = {
    "none": "blnone",
    "mild_cubic": "blmild",
    "strong_curved": "blstrong",
}


# --------------------------------------------------------------------------- #
# Peak and case containers
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Peak:
    """One generator band (area-parameterized)."""

    name: str
    center: float
    fwhm: float
    area: float
    lineshape: str  # "lorentzian" | "gaussian"


@dataclass(frozen=True)
class Case:
    """Factor combination defining one synthetic spectrum.

    ``recovery`` cases are the noise-free, baseline-free, spike-free spectra used
    by Gate V1; for them ``snr_label`` is ``None``, ``baseline_label`` is
    ``"none"`` and ``spike`` is ``False``.
    """

    stage: int
    ratio: float
    baseline_label: str
    snr_label: int | None
    spike: bool
    recovery: bool


# --------------------------------------------------------------------------- #
# Analytic band helpers (delegate all line-shape math to lineshapes.py)
# --------------------------------------------------------------------------- #
def _height(peak: Peak) -> float:
    """Analytic peak height (line-shape maximum) of ``peak``."""
    if peak.lineshape == "lorentzian":
        return float(lineshapes.lorentzian_height_from_area(peak.area, peak.fwhm))
    if peak.lineshape == "gaussian":
        return float(lineshapes.gaussian_height_from_area(peak.area, peak.fwhm))
    raise ValueError(f"unknown lineshape {peak.lineshape!r}")


def _eval(peak: Peak, x: np.ndarray) -> np.ndarray:
    """Noiseless contribution of ``peak`` over ``x``."""
    if peak.lineshape == "lorentzian":
        return lineshapes.lorentzian(x, peak.center, peak.area, peak.fwhm)
    if peak.lineshape == "gaussian":
        return lineshapes.gaussian(x, peak.center, peak.area, peak.fwhm)
    raise ValueError(f"unknown lineshape {peak.lineshape!r}")


def _stage1_peaks(ratio: float) -> list[Peak]:
    """Stage-1 bands: Lorentzian D, G, and weak D-prime.

    D/G area ratio is ``ratio``; D-prime carries 15% of D's *area*.
    """
    g_area = G_AREA_BASE
    d_area = ratio * g_area
    dprime_area = 0.15 * d_area
    return [
        Peak("D", 1350.0, 35.0, d_area, "lorentzian"),
        Peak("G", 1585.0, 22.0, g_area, "lorentzian"),
        Peak("Dprime", 1620.0, 18.0, dprime_area, "lorentzian"),
    ]


def _stage2_peaks(ratio: float = STAGE2_RATIO) -> list[Peak]:
    """Stage-2 bands: Lorentzian D, G; Gaussian D3, D4.

    D/G area ratio is ``ratio`` (fixed 1.0 for the suite); D3 and D4 each carry
    30% of G's *area*.
    """
    g_area = G_AREA_BASE
    d_area = ratio * g_area
    sat_area = 0.30 * g_area
    return [
        Peak("D", 1350.0, 90.0, d_area, "lorentzian"),
        Peak("G", 1585.0, 70.0, g_area, "lorentzian"),
        Peak("D3", 1500.0, 120.0, sat_area, "gaussian"),
        Peak("D4", 1200.0, 140.0, sat_area, "gaussian"),
    ]


def _peaks_for(case: Case) -> list[Peak]:
    return _stage1_peaks(case.ratio) if case.stage == 1 else _stage2_peaks(case.ratio)


def _grid_for(case: Case) -> tuple[float, float, float]:
    return GRID_NO_D4 if case.stage == 1 else GRID_WITH_D4


# --------------------------------------------------------------------------- #
# Naming
# --------------------------------------------------------------------------- #
def _ratio_tag(ratio: float) -> str:
    """``0.1 -> r0p1``, ``1.0 -> r1p0``, ``2.0 -> r2p0``."""
    return f"r{ratio:.1f}".replace(".", "p")


def case_id(case: Case) -> str:
    """Unique filename stem encoding every case factor."""
    tag = _ratio_tag(case.ratio)
    if case.recovery:
        return f"tierA_stage{case.stage}_{tag}_recovery"
    stem = (
        f"tierA_stage{case.stage}_{tag}"
        f"_{_BASELINE_TAG[case.baseline_label]}_snr{case.snr_label}"
    )
    if case.spike:
        stem += "_spike"
    return stem


# --------------------------------------------------------------------------- #
# Deterministic stochastic effects (noise, baseline, spikes)
# --------------------------------------------------------------------------- #
def _case_rng(case: Case, seed: int) -> np.random.Generator:
    """Per-case generator: same ``seed`` + factors -> identical draws."""
    key = zlib.crc32(case_id(case).encode("utf-8"))
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(key)]))


def _baseline_curve(label: str, x: np.ndarray, signal_max: float) -> np.ndarray:
    """Deterministic background scaled to the signal height.

    ``mild_cubic`` is a gentle cubic at 5% of the peak height; ``strong_curved``
    is a broad Gaussian hump at 40%.  Both are smooth and signal-relative so the
    same shape applies across grids.
    """
    if label == "none":
        return np.zeros_like(x)
    u = (x - x[0]) / (x[-1] - x[0])  # normalized 0..1
    if label == "mild_cubic":
        # Gentle S-shaped cubic, range ~[0, 1] * 0.05 * signal_max.
        shape = 1.0 - 3.0 * u**2 + 2.0 * u**3
        return 0.05 * signal_max * shape
    if label == "strong_curved":
        shape = np.exp(-(((u - 0.5) / 0.4) ** 2))
        return 0.40 * signal_max * shape
    raise ValueError(f"unknown baseline label {label!r}")


def _add_noise(y: np.ndarray, snr: int, signal_max: float, rng) -> np.ndarray:
    """Additive Gaussian noise with sigma = signal_max / SNR (A2)."""
    sigma = signal_max / float(snr)
    return y + rng.normal(0.0, sigma, size=y.size)


def _add_spikes(y: np.ndarray, signal_max: float, rng) -> np.ndarray:
    """Inject a few single-channel cosmic spikes (optional generator effect)."""
    y = y.copy()
    n_spikes = 3
    idx = rng.choice(y.size, size=n_spikes, replace=False)
    y[idx] = y[idx] + rng.uniform(5.0, 10.0, size=n_spikes) * signal_max
    return y


# --------------------------------------------------------------------------- #
# Truth record
# --------------------------------------------------------------------------- #
def _truth(case: Case, peaks: list[Peak], grid, seed: int) -> dict:
    """Ground-truth record computed purely from the generator band parameters."""
    lo, hi, step = grid
    by_name = {p.name: p for p in peaks}
    d, g = by_name["D"], by_name["G"]

    d_area, g_area = float(d.area), float(g.area)
    d_height, g_height = _height(d), _height(g)

    return {
        "case_id": case_id(case),
        "stage": case.stage,
        "recovery": case.recovery,
        "seed": int(seed),
        "wavelength_nm": WAVELENGTH_NM,
        "grid": {"min": float(lo), "max": float(hi), "step": float(step)},
        "baseline_label": case.baseline_label,
        "snr_label": case.snr_label,  # int or None
        "spike": bool(case.spike),
        "id_ig_area_ratio_nominal": float(case.ratio),
        "peaks": [
            {
                "name": p.name,
                "center": float(p.center),
                "fwhm": float(p.fwhm),
                "area": float(p.area),
                "height": _height(p),
                "lineshape": p.lineshape,
                "stage": case.stage,
            }
            for p in peaks
        ],
        # Both pre-registered truth definitions, unambiguously labelled.
        "true_id_ig_area": d_area / g_area,
        "true_id_ig_height": d_height / g_height,
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate(case: Case, seed: int = SEED) -> tuple[Spectrum, dict]:
    """Generate one Tier-A spectrum and its analytic truth.

    Returns ``(spectrum, truth_dict)``.  The truth is derived from the noiseless,
    baseline-free band functions only -- never from the returned curve.
    """
    peaks = _peaks_for(case)
    lo, hi, step = _grid_for(case)
    # Inclusive grid; +0.5*step guards float endpoint loss.
    x = np.arange(lo, hi + 0.5 * step, step, dtype=float)

    signal = np.zeros_like(x)
    for peak in peaks:
        signal = signal + _eval(peak, x)
    signal_max = float(np.max(signal))

    y = signal + _baseline_curve(case.baseline_label, x, signal_max)

    if case.snr_label is not None or case.spike:
        rng = _case_rng(case, seed)
        if case.snr_label is not None:
            y = _add_noise(y, case.snr_label, signal_max, rng)
        if case.spike:
            y = _add_spikes(y, signal_max, rng)

    truth = _truth(case, peaks, (lo, hi, step), seed)
    spec = load_spectrum(
        x, y, WAVELENGTH_NM, meta={"case_id": truth["case_id"]}
    )
    return spec, truth


def enumerate_cases() -> list[Case]:
    """The full Tier-A suite: recovery cases + the noisy factorial.

    * Gate V1 recovery (noise-free, baseline-free): stage 1 x 4 ratios, stage 2 x 1.
    * Noisy factorial: stage-1 ratio(4) x baseline(3) x SNR(3) plus
      stage-2 baseline(3) x SNR(3).

    Cosmic spikes are an optional generator capability (see :func:`generate`) and
    are deliberately *not* crossed as a suite dimension.
    """
    cases: list[Case] = []

    # Recovery / Gate-V1 cases.
    for ratio in STAGE1_RATIOS:
        cases.append(
            Case(1, ratio, "none", None, spike=False, recovery=True)
        )
    cases.append(
        Case(2, STAGE2_RATIO, "none", None, spike=False, recovery=True)
    )

    # Noisy factorial, stage 1.
    for ratio in STAGE1_RATIOS:
        for bl in BASELINE_LABELS:
            for snr in SNR_LEVELS:
                cases.append(Case(1, ratio, bl, snr, spike=False, recovery=False))

    # Noisy factorial, stage 2 (fixed ratio).
    for bl in BASELINE_LABELS:
        for snr in SNR_LEVELS:
            cases.append(
                Case(2, STAGE2_RATIO, bl, snr, spike=False, recovery=False)
            )

    return cases


def recovery_cases() -> list[Case]:
    """Just the noise-free, baseline-free Gate V1 cases."""
    return [c for c in enumerate_cases() if c.recovery]


def suite(out_dir, seed: int = SEED) -> Path:
    """Write the full Tier-A suite (CSV + ``*_truth.json`` + manifest).

    Each case yields one CSV (columns ``shift_cm-1,intensity``) and one matching
    ``*_truth.json`` sharing the filename stem.  A ``manifest.csv`` lists every
    case_id and its factors for a one-to-one pairing audit.  Returns the output
    directory.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Clear suite-managed outputs first so a re-run with a *different* case set
    # cannot leave stale orphan CSV/JSON behind (which would silently corrupt the
    # one-to-one pairing audit).  Only the files this function writes are removed
    # -- the top-level CSVs, ``*_truth.json`` records and ``manifest.csv`` -- so
    # sibling artefacts such as the ``figures/`` subdirectory are left untouched.
    for stale in (*out.glob("*.csv"), *out.glob("*_truth.json")):
        stale.unlink()

    manifest_rows = []
    for case in enumerate_cases():
        spec, truth = generate(case, seed)
        stem = truth["case_id"]

        csv_path = out / f"{stem}.csv"
        json_path = out / f"{stem}_truth.json"

        pd.DataFrame(
            {"shift_cm-1": spec.shift, "intensity": spec.intensity}
        ).to_csv(csv_path, index=False)

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(truth, fh, indent=2, sort_keys=True)

        manifest_rows.append(
            {
                "case_id": stem,
                "stage": case.stage,
                "ratio": case.ratio,
                "baseline_label": case.baseline_label,
                "snr_label": case.snr_label,
                "spike": case.spike,
                "recovery": case.recovery,
                "csv": csv_path.name,
                "truth_json": json_path.name,
                "true_id_ig_area": truth["true_id_ig_area"],
                "true_id_ig_height": truth["true_id_ig_height"],
            }
        )

    pd.DataFrame(manifest_rows).to_csv(out / "manifest.csv", index=False)
    return out


__all__ = [
    "SEED",
    "Peak",
    "Case",
    "generate",
    "enumerate_cases",
    "recovery_cases",
    "suite",
    "case_id",
]
