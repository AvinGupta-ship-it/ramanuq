"""Construction of adversarial ("hostile") spectra that stress the pipeline.

Tier B is the *out-of-family* synthetic suite.  Unlike Tier A (which renders every
band with one of the two analytic families the fitter can represent, Lorentzian or
Gaussian), Tier B deliberately builds bands the fitter *cannot* represent exactly:

* :func:`composite_band` -- a sum of 3-7 jittered narrow Lorentzians whose
  aggregate is **not** a single Lorentzian (inhomogeneous broadening);
* :func:`emg_band` -- a Gaussian core convolved with a one-sided exponential of
  time-constant ``tau``, giving an asymmetric (exponentially-modified) profile;
* :func:`mixed_voigt_band` -- a pseudo-Voigt with a per-band mixing fraction
  ``eta`` (different Lorentzian/Gaussian blends across bands).

The background is a *smooth random* baseline, :func:`gp_baseline`: a sum of broad
random Gaussians plus a decaying exponential, at severities ``none|mild|strong``.
The name "gp_baseline" is a **label only** -- this is NOT a Gaussian-process
regressor and imports no GP library; the specification is exactly "broad random
Gaussians plus a decaying exponential."

Operational ground-truth (pre-registered, validation_plan.md S2): true band
intensities come from the generator's *noiseless, baseline-free* band functions.
Because the Tier-B band functions have no closed-form integral, the true area is
the numeric integral of the band callable over the spectrum grid and the true
height is its maximum.  Both ``true_id_ig_area`` and ``true_id_ig_height`` are
stored per spectrum.  Truth is computed BEFORE the baseline and noise are added
and is never read back off the observed curve.

Determinism is anchored to the single project seed :data:`SEED` (shared with
:mod:`ramanuq.synth`).  All randomness for a case derives from a
:class:`numpy.random.SeedSequence` mixing ``SEED`` with the case id, so the same
seed reproduces every spectrum and truth record bit-for-bit, while distinct cases
stay independent.
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
from .synth import (
    G_AREA_BASE,
    GRID_NO_D4,
    GRID_WITH_D4,
    SEED,
    WAVELENGTH_NM,
)

# --------------------------------------------------------------------------- #
# Tier-B suite constants (the full crossing)
# --------------------------------------------------------------------------- #
#: Baseline severities (smooth random background).
SEVERITIES = ("none", "mild", "strong")
#: Per-severity overall amplitude as a fraction of the signal height.
_SEVERITY_FRAC = {"none": 0.0, "mild": 0.15, "strong": 0.6}

#: Signal-to-noise levels (additive Gaussian noise, sigma = signal_max / SNR).
SNR_LEVELS = (200, 50, 15)

#: Random instances per (stage, severity, SNR) cell.
N_INSTANCES = 5

#: Nominal D and G total areas (the realized I_D/I_G is measured from the
#: out-of-family callables, not from these targets).
_D_AREA = G_AREA_BASE
_G_AREA = G_AREA_BASE

# Gaussian FWHM -> sigma.
_GAUSS_SIGMA_FACTOR = 1.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))

_BL_TAG = {"none": "blnone", "mild": "blmild", "strong": "blstrong"}


# --------------------------------------------------------------------------- #
# Case container and naming
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Case:
    """One Tier-B factor combination (stage x severity x SNR x instance)."""

    stage: int  # 1 or 2
    severity: str  # "none" | "mild" | "strong"
    snr: int  # 200 | 50 | 15
    instance: int  # 0 .. N_INSTANCES-1


def case_id(case: Case) -> str:
    """Unique filename stem encoding every Tier-B factor."""
    return (
        f"tierB_stage{case.stage}_{_BL_TAG[case.severity]}"
        f"_snr{case.snr}_i{case.instance}"
    )


def _case_rng(case: Case, seed: int) -> np.random.Generator:
    """Per-case generator: same ``seed`` + factors -> identical draws."""
    key = zlib.crc32(case_id(case).encode("utf-8"))
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(key)]))


def _grid_for(case: Case) -> tuple[float, float, float]:
    return GRID_NO_D4 if case.stage == 1 else GRID_WITH_D4


# --------------------------------------------------------------------------- #
# Out-of-family band constructors.  Each returns (callable, params).
# --------------------------------------------------------------------------- #
def composite_band(
    rng: np.random.Generator,
    center: float,
    total_area: float,
    name: str = "band",
) -> tuple[object, dict]:
    """Sum of 3-7 jittered narrow Lorentzians (a non-Lorentzian aggregate).

    The sub-peaks share ``total_area`` (split by random weights) and sit within
    +/-25 cm^-1 of ``center`` with narrow widths, so the summed profile is bumpy
    and asymmetric -- out of the single-Lorentzian family the fitter assumes.
    The returned ``params`` records every sub-peak's center, FWHM, area and
    (analytic) height; the *band* height truth is the max of the summed callable,
    never the sum of the sub-peak heights.
    """
    n_sub = int(rng.integers(3, 8))  # 3..7 inclusive
    centers = center + rng.uniform(-25.0, 25.0, n_sub)
    fwhms = rng.uniform(8.0, 25.0, n_sub)
    weights = rng.uniform(0.5, 1.5, n_sub)
    weights = weights / weights.sum()
    areas = total_area * weights
    heights = [
        float(lineshapes.lorentzian_height_from_area(a, w))
        for a, w in zip(areas, fwhms)
    ]

    def f(x):
        x = np.asarray(x, dtype=float)
        out = np.zeros_like(x)
        for c, a, w in zip(centers, areas, fwhms):
            out = out + lineshapes.lorentzian(x, c, a, w)
        return out

    params = {
        "name": name,
        "family": "composite_lorentzians",
        "nominal_center": float(center),
        "total_area": float(total_area),
        "n_sub": n_sub,
        "sub_centers": [float(c) for c in centers],
        "sub_fwhms": [float(w) for w in fwhms],
        "sub_areas": [float(a) for a in areas],
        "sub_heights": heights,
    }
    return f, params


def emg_band(
    rng: np.random.Generator,
    center: float,
    total_area: float,
    name: str = "band",
    core_fwhm: float | None = None,
    tau: float | None = None,
) -> tuple[object, dict]:
    """Gaussian core convolved with a one-sided exponential (asymmetric profile).

    The exponential of time-constant ``tau`` adds a one-sided tail toward higher
    Raman shift, producing an exponentially-modified-Gaussian (EMG) shape that no
    symmetric Lorentzian/Gaussian/pseudo-Voigt can match.  The callable evaluates
    on a *uniform* grid (the spectrum axis); it convolves on a padded copy of that
    grid to avoid edge artefacts, then rescales so the numeric area equals
    ``total_area``.
    """
    fwhm = float(core_fwhm if core_fwhm is not None else rng.uniform(28.0, 45.0))
    sigma = fwhm * _GAUSS_SIGMA_FACTOR
    tau = float(tau if tau is not None else rng.uniform(15.0, 40.0))

    def f(x):
        x = np.asarray(x, dtype=float)
        h = float(x[1] - x[0])
        pad = int(np.ceil((6.0 * sigma + 8.0 * tau) / h))
        left = x[0] + h * np.arange(-pad, 0)
        right = x[-1] + h * np.arange(1, pad + 1)
        xx = np.concatenate([left, x, right])
        core = np.exp(-0.5 * ((xx - center) / sigma) ** 2)
        # One-sided (causal) exponential kernel: mass added toward higher shift.
        tk = np.arange(0.0, 8.0 * tau, h)
        kern = np.exp(-tk / tau)
        full = np.convolve(core, kern, mode="full")[: xx.size]
        prof = full[pad : pad + x.size]
        area = float(np.trapezoid(prof, x))
        if area <= 0.0:
            return prof
        return prof * (total_area / area)

    params = {
        "name": name,
        "family": "emg",
        "center": float(center),
        "core_fwhm": fwhm,
        "tau": tau,
        "total_area": float(total_area),
    }
    return f, params


def mixed_voigt_band(
    rng: np.random.Generator,
    center: float,
    total_area: float,
    eta: float,
    fwhm: float,
    name: str = "band",
) -> tuple[object, dict]:
    """Pseudo-Voigt with a fixed per-band mixing fraction ``eta``.

    ``eta`` is the Lorentzian weight (``1-eta`` Gaussian).  Distinct bands are
    assigned distinct ``eta`` by the caller, so the suite carries a mix of
    blend fractions the fixed-lineshape fitter cannot match simultaneously.
    """
    eta = float(eta)
    fwhm = float(fwhm)

    def f(x):
        x = np.asarray(x, dtype=float)
        return lineshapes.pseudo_voigt(x, center, total_area, fwhm, eta)

    params = {
        "name": name,
        "family": "mixed_voigt",
        "center": float(center),
        "fwhm": fwhm,
        "area": float(total_area),
        "eta": eta,
    }
    return f, params


def gp_baseline(severity: str, seed: int) -> tuple[object, dict]:
    """Smooth random baseline: broad random Gaussians + a decaying exponential.

    NOT a Gaussian-process regressor and importing no GP library -- the name is a
    label only.  ``severity`` in ``none|mild|strong`` sets the overall amplitude
    as a fraction of the signal height (the caller multiplies the callable by the
    signal scale).  The callable returns a background in those relative units; at
    ``none`` it is identically zero.
    """
    if severity not in _SEVERITY_FRAC:
        raise ValueError(
            f"unknown severity {severity!r}; expected one of {SEVERITIES}"
        )
    frac = _SEVERITY_FRAC[severity]
    if frac == 0.0:

        def f(x):
            return np.zeros_like(np.asarray(x, dtype=float))

        return f, {
            "severity": severity,
            "frac": 0.0,
            "gaussians": [],
            "exp": None,
        }

    rng = np.random.default_rng(
        np.random.SeedSequence(
            [int(seed), zlib.crc32(f"gp_baseline_{severity}".encode("utf-8"))]
        )
    )
    n_g = int(rng.integers(2, 5))  # 2..4 broad Gaussians
    g_centers = rng.uniform(900.0, 1900.0, n_g)
    g_widths = rng.uniform(150.0, 500.0, n_g)  # broad
    g_amps = rng.uniform(0.3, 1.0, n_g)
    exp_amp = float(rng.uniform(0.5, 1.0))
    exp_decay = float(rng.uniform(300.0, 900.0))  # cm^-1 decay scale

    def f(x):
        x = np.asarray(x, dtype=float)
        b = np.zeros_like(x)
        for c, w, a in zip(g_centers, g_widths, g_amps):
            b = b + a * np.exp(-0.5 * ((x - c) / w) ** 2)
        b = b + exp_amp * np.exp(-(x - x[0]) / exp_decay)
        peak = float(np.max(b))
        if peak > 0.0:
            b = frac * b / peak
        return b

    params = {
        "severity": severity,
        "frac": float(frac),
        "gaussians": [
            {"center": float(c), "width": float(w), "amp": float(a)}
            for c, w, a in zip(g_centers, g_widths, g_amps)
        ],
        "exp": {"amp": exp_amp, "decay": exp_decay},
    }
    return f, params


# --------------------------------------------------------------------------- #
# Band assembly per case
# --------------------------------------------------------------------------- #
@dataclass
class Assembled:
    """Everything needed to write or plot a Tier-B case (no truth read-back)."""

    case: Case
    x: np.ndarray
    components: dict  # name -> noiseless, baseline-free band values
    band_params: list  # ordered generator params per band
    signal: np.ndarray  # sum of components
    signal_max: float
    baseline: np.ndarray  # added background (absolute units)
    baseline_params: dict
    observed: np.ndarray  # signal + baseline + noise
    truth: dict


def _build_bands(case: Case, rng: np.random.Generator):
    """Construct the ordered (callable, params) bands for ``case``.

    D is always a composite band and G an EMG band (the two carry the I_D/I_G
    truth); satellites are mixed-Voigt bands with distinct per-band ``eta``.
    """
    bands = []
    d_call, d_par = composite_band(rng, 1350.0, _D_AREA, name="D")
    g_call, g_par = emg_band(rng, 1585.0, _G_AREA, name="G")
    bands.append(("D", d_call, d_par))
    bands.append(("G", g_call, g_par))

    if case.stage == 1:
        dp_call, dp_par = mixed_voigt_band(
            rng, 1620.0, 0.15 * _D_AREA, eta=float(rng.uniform(0.3, 0.7)),
            fwhm=18.0, name="Dprime",
        )
        bands.append(("Dprime", dp_call, dp_par))
    else:
        d3_call, d3_par = mixed_voigt_band(
            rng, 1500.0, 0.30 * _G_AREA, eta=float(rng.uniform(0.2, 0.5)),
            fwhm=120.0, name="D3",
        )
        d4_call, d4_par = mixed_voigt_band(
            rng, 1200.0, 0.30 * _G_AREA, eta=float(rng.uniform(0.5, 0.8)),
            fwhm=140.0, name="D4",
        )
        bands.append(("D3", d3_call, d3_par))
        bands.append(("D4", d4_call, d4_par))

    return bands


def assemble(case: Case, seed: int = SEED) -> Assembled:
    """Build a Tier-B case end to end (components, baseline, noise, truth)."""
    rng = _case_rng(case, seed)
    lo, hi, step = _grid_for(case)
    x = np.arange(lo, hi + 0.5 * step, step, dtype=float)

    bands = _build_bands(case, rng)
    components = {name: call(x) for name, call, _ in bands}
    band_params = [par for _, _, par in bands]
    signal = np.zeros_like(x)
    for name in components:
        signal = signal + components[name]
    signal_max = float(np.max(signal))

    # Truth from the NOISELESS, BASELINE-FREE band callables only.
    d_vals = components["D"]
    g_vals = components["G"]
    true_area = float(np.trapezoid(d_vals, x)) / float(np.trapezoid(g_vals, x))
    true_height = float(np.max(d_vals)) / float(np.max(g_vals))

    # Smooth random background, scaled to the signal height, then noise.
    bl_seed = int(zlib.crc32(case_id(case).encode("utf-8")) ^ int(seed))
    bl_call, bl_par = gp_baseline(case.severity, bl_seed)
    baseline = signal_max * bl_call(x)
    observed = signal + baseline
    sigma = signal_max / float(case.snr)
    observed = observed + rng.normal(0.0, sigma, size=x.size)

    families = sorted({p["family"] for p in band_params})
    truth = {
        "case_id": case_id(case),
        "tier": "B",
        "stage": case.stage,
        "stage_label": f"stage{case.stage}",
        "severity": case.severity,
        "snr_label": int(case.snr),
        "instance": int(case.instance),
        "seed": int(seed),
        "wavelength_nm": WAVELENGTH_NM,
        "grid": {"min": float(lo), "max": float(hi), "step": float(step)},
        "generator_families": families,
        "bands": band_params,
        "baseline": {
            **bl_par,
            "signal_scale": signal_max,
        },
        "id_ig_area_ratio_nominal": float(_D_AREA / _G_AREA),
        "true_id_ig_area": true_area,
        "true_id_ig_height": true_height,
    }

    return Assembled(
        case=case,
        x=x,
        components=components,
        band_params=band_params,
        signal=signal,
        signal_max=signal_max,
        baseline=baseline,
        baseline_params=truth["baseline"],
        observed=observed,
        truth=truth,
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate(case: Case, seed: int = SEED) -> tuple[Spectrum, dict]:
    """Generate one Tier-B spectrum and its truth.

    Returns ``(spectrum, truth_dict)``.  Truth is derived from the noiseless,
    baseline-free band callables only -- never from the returned curve.
    """
    built = assemble(case, seed)
    spec = load_spectrum(
        built.x, built.observed, WAVELENGTH_NM, meta={"case_id": built.truth["case_id"]}
    )
    return spec, built.truth


def enumerate_cases() -> list[Case]:
    """The full Tier-B crossing: stage(2) x severity(3) x SNR(3) x instance(5) = 90."""
    cases: list[Case] = []
    for stage in (1, 2):
        for severity in SEVERITIES:
            for snr in SNR_LEVELS:
                for inst in range(N_INSTANCES):
                    cases.append(Case(stage, severity, snr, inst))
    return cases


def suite(out_dir, seed: int = SEED) -> Path:
    """Write the full Tier-B suite (CSV + ``*_truth.json`` + manifest).

    Each case yields one CSV (columns ``shift_cm-1,intensity``) and one matching
    ``*_truth.json`` sharing the filename stem.  A ``manifest.csv`` lists every
    case for a one-to-one pairing audit.  Returns the output directory.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Clear suite-managed outputs first so a re-run cannot leave stale orphans
    # behind (which would corrupt the one-to-one pairing audit).  Only the files
    # this function writes are removed; siblings such as ``figures/`` are kept.
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
                "severity": case.severity,
                "snr_label": case.snr,
                "instance": case.instance,
                "csv": csv_path.name,
                "truth_json": json_path.name,
                "generator_families": ";".join(truth["generator_families"]),
                "true_id_ig_area": truth["true_id_ig_area"],
                "true_id_ig_height": truth["true_id_ig_height"],
            }
        )

    pd.DataFrame(manifest_rows).to_csv(out / "manifest.csv", index=False)
    return out


__all__ = [
    "SEED",
    "SEVERITIES",
    "SNR_LEVELS",
    "N_INSTANCES",
    "Case",
    "case_id",
    "composite_band",
    "emg_band",
    "mixed_voigt_band",
    "gp_baseline",
    "assemble",
    "generate",
    "enumerate_cases",
    "suite",
]
