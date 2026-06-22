"""Tests for the Tier-B (out-of-family, "hostile") generator (:mod:`ramanuq.hostile`).

These check the *generator contract* independently of the fitter: determinism,
truth-schema completeness (both labelled ratios, every generator parameter, the
seed, baseline metadata + severity, generator-family labels), finiteness, a
strictly increasing Raman-shift axis, parseable one-to-one filenames, the full
90-cell crossing, physically valid parameters, and -- crucially -- that each
composite/EMG band really is *out of family*: the best independent single
Lorentzian leaves a relative RMS residual above 1%.  Tier-A artefacts and the
Day-5 module stubs must stay untouched.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import curve_fit

from ramanuq import hostile, lineshapes

_REPO = Path(__file__).resolve().parents[1]
_TIERA = _REPO / "data" / "synthetic" / "tierA"
_SRC = _REPO / "src" / "ramanuq"

_ALL_CASES = hostile.enumerate_cases()

#: case_id -> (stage, severity, snr, instance).
_CASE_RE = re.compile(
    r"^tierB_stage(?P<stage>[12])_bl(?P<sev>none|mild|strong)"
    r"_snr(?P<snr>\d+)_i(?P<inst>\d+)$"
)


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "case",
    [
        hostile.Case(1, "none", 200, 0),
        hostile.Case(1, "strong", 15, 3),
        hostile.Case(2, "mild", 50, 2),
    ],
    ids=hostile.case_id,
)
def test_same_seed_reproduces_arrays_and_truth(case):
    """Same seed -> numerically identical spectrum and truth record."""
    s1, t1 = hostile.generate(case, seed=hostile.SEED)
    s2, t2 = hostile.generate(case, seed=hostile.SEED)
    assert np.array_equal(s1.shift, s2.shift)
    assert np.array_equal(s1.intensity, s2.intensity)
    assert t1 == t2


def test_distinct_cases_are_independent():
    """Different cells produce different observed spectra (independent draws)."""
    a, _ = hostile.generate(hostile.Case(1, "mild", 50, 0))
    b, _ = hostile.generate(hostile.Case(1, "mild", 50, 1))
    assert not np.array_equal(a.intensity, b.intensity)


# --------------------------------------------------------------------------- #
# Truth-schema completeness
# --------------------------------------------------------------------------- #
_REQUIRED_TRUTH_KEYS = {
    "case_id",
    "tier",
    "stage",
    "severity",
    "snr_label",
    "instance",
    "seed",
    "wavelength_nm",
    "grid",
    "generator_families",
    "bands",
    "baseline",
    "true_id_ig_area",
    "true_id_ig_height",
}


@pytest.mark.parametrize("case", _ALL_CASES, ids=hostile.case_id)
def test_truth_schema_complete(case):
    """Every truth record carries both ratios, the seed, all params and metadata."""
    _, truth = hostile.generate(case)
    assert _REQUIRED_TRUTH_KEYS <= set(truth), (
        f"missing truth keys: {_REQUIRED_TRUTH_KEYS - set(truth)}"
    )

    # Both pre-registered truth definitions present, labelled, finite, positive.
    for key in ("true_id_ig_area", "true_id_ig_height"):
        assert key in truth
        assert np.isfinite(truth[key]) and truth[key] > 0

    # Seed recorded.
    assert truth["seed"] == hostile.SEED
    # Grid fully described.
    assert {"min", "max", "step"} <= set(truth["grid"])
    # Generator-family label(s) present and non-empty.
    assert truth["generator_families"]
    # Baseline metadata + severity present.
    assert truth["baseline"]["severity"] == truth["severity"]
    assert "frac" in truth["baseline"]
    assert "signal_scale" in truth["baseline"]


@pytest.mark.parametrize("case", _ALL_CASES, ids=hostile.case_id)
def test_band_params_complete_per_family(case):
    """Each band stores its full generator parameter set for its family."""
    _, truth = hostile.generate(case)
    names = {b["name"] for b in truth["bands"]}
    assert {"D", "G"} <= names  # I_D/I_G carriers always present

    for band in truth["bands"]:
        fam = band["family"]
        if fam == "composite_lorentzians":
            assert band["n_sub"] == len(band["sub_centers"])
            assert len(band["sub_fwhms"]) == band["n_sub"]
            assert len(band["sub_heights"]) == band["n_sub"]
            assert len(band["sub_areas"]) == band["n_sub"]
        elif fam == "emg":
            assert "tau" in band and "core_fwhm" in band
        elif fam == "mixed_voigt":
            assert "eta" in band and 0.0 <= band["eta"] <= 1.0
        else:
            raise AssertionError(f"unexpected band family {fam!r}")


def test_truth_height_is_max_of_summed_composite_callable():
    """Composite D height truth is the max of the SUM, not the sum of sub-heights."""
    case = hostile.Case(1, "none", 200, 0)
    built = hostile.assemble(case)
    d = built.components["D"]
    d_band = next(b for b in built.truth["bands"] if b["name"] == "D")
    summed_height = float(np.max(d))
    naive_sum = float(sum(d_band["sub_heights"]))
    g_height = float(np.max(built.components["G"]))
    # Stored height ratio uses the summed-callable max, distinct from the naive sum.
    assert built.truth["true_id_ig_height"] == pytest.approx(summed_height / g_height)
    assert summed_height < naive_sum  # overlap never adds to the full sum


# --------------------------------------------------------------------------- #
# Spectrum integrity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _ALL_CASES, ids=hostile.case_id)
def test_spectrum_finite_and_axis_strictly_increasing(case):
    """Finite intensities/shifts; strictly increasing Raman-shift axis."""
    spec, truth = hostile.generate(case)
    assert np.all(np.isfinite(spec.shift))
    assert np.all(np.isfinite(spec.intensity))
    diffs = np.diff(spec.shift)
    assert np.all(diffs > 0)
    assert np.allclose(diffs, truth["grid"]["step"])


# --------------------------------------------------------------------------- #
# Physically valid generator parameters
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _ALL_CASES, ids=hostile.case_id)
def test_generator_params_physically_valid(case):
    """Positive widths, plausible centers, non-negative areas."""
    _, truth = hostile.generate(case)
    for band in truth["bands"]:
        if band["family"] == "composite_lorentzians":
            for c in band["sub_centers"]:
                assert 800.0 <= c <= 1900.0
            for w in band["sub_fwhms"]:
                assert w > 0.0
            for a in band["sub_areas"]:
                assert a >= 0.0
            assert band["total_area"] >= 0.0
        elif band["family"] == "emg":
            assert 800.0 <= band["center"] <= 1900.0
            assert band["core_fwhm"] > 0.0
            assert band["tau"] > 0.0
            assert band["total_area"] >= 0.0
        else:  # mixed_voigt
            assert 800.0 <= band["center"] <= 1900.0
            assert band["fwhm"] > 0.0
            assert band["area"] >= 0.0


# --------------------------------------------------------------------------- #
# Out-of-family proof (non-Lorentzianity)
# --------------------------------------------------------------------------- #
def _best_single_lorentzian_rel_resid(x, y):
    """Relative RMS residual of the BEST independent single-Lorentzian fit.

    This is a real least-squares fit of an area-parameterized Lorentzian to the
    band -- not a comparison of the band to itself -- so a large residual proves
    the band is out of the single-Lorentzian family.
    """
    p0 = [float(x[np.argmax(y)]), float(np.trapezoid(y, x)), 30.0]
    popt, _ = curve_fit(
        lambda xx, c, a, w: lineshapes.lorentzian(xx, c, a, w),
        x, y, p0=p0, maxfev=40000,
    )
    fit = lineshapes.lorentzian(x, *popt)
    return float(np.sqrt(np.mean((y - fit) ** 2)) / np.sqrt(np.mean(y**2)))


@pytest.mark.parametrize("case", _ALL_CASES, ids=hostile.case_id)
def test_composite_and_emg_bands_are_out_of_family(case):
    """Each composite/EMG band's best single-Lorentzian fit leaves >1% rel RMS."""
    built = hostile.assemble(case)
    comp = _best_single_lorentzian_rel_resid(built.x, built.components["D"])
    emg = _best_single_lorentzian_rel_resid(built.x, built.components["G"])
    assert comp > 0.01, f"composite D too Lorentzian ({comp:.4f}) for {built.truth['case_id']}"
    assert emg > 0.01, f"emg G too Lorentzian ({emg:.4f}) for {built.truth['case_id']}"


# --------------------------------------------------------------------------- #
# Suite-level: coverage, naming, pairing
# --------------------------------------------------------------------------- #
def test_full_crossing_is_90_cells():
    """stage(2) x severity(3) x SNR(3) x instance(5) = 90, no duplicates."""
    assert len(_ALL_CASES) == 90
    keys = {(c.stage, c.severity, c.snr, c.instance) for c in _ALL_CASES}
    assert len(keys) == 90
    assert {c.stage for c in _ALL_CASES} == {1, 2}
    assert {c.severity for c in _ALL_CASES} == set(hostile.SEVERITIES)
    assert {c.snr for c in _ALL_CASES} == set(hostile.SNR_LEVELS)
    assert {c.instance for c in _ALL_CASES} == set(range(hostile.N_INSTANCES))


def test_case_ids_unique_parseable_and_consistent():
    """Every case_id is unique, filesystem-safe, and round-trips its factors."""
    ids = [hostile.case_id(c) for c in _ALL_CASES]
    assert len(ids) == len(set(ids))
    for case, cid in zip(_ALL_CASES, ids):
        assert all(ch.isalnum() or ch in "_-" for ch in cid)
        m = _CASE_RE.match(cid)
        assert m, f"unparseable case_id {cid!r}"
        assert int(m["stage"]) == case.stage
        assert m["sev"] == case.severity
        assert int(m["snr"]) == case.snr
        assert int(m["inst"]) == case.instance


def test_suite_writes_one_to_one_csv_json_pairs(tmp_path):
    """suite() writes exactly one CSV and one matching *_truth.json per case."""
    out = hostile.suite(tmp_path)
    csvs = sorted(p.stem for p in out.glob("*.csv") if p.name != "manifest.csv")
    jsons = sorted(p.name[: -len("_truth.json")] for p in out.glob("*_truth.json"))
    assert len(csvs) == 90
    assert csvs == jsons  # exact one-to-one pairing by stem
    assert len(set(csvs)) == 90  # no duplicate case ids
    assert (out / "manifest.csv").exists()


def test_suite_csv_schema_and_truth_loadable(tmp_path):
    """CSVs use the Day-3 columns; each truth JSON is valid and complete."""
    out = hostile.suite(tmp_path)
    for case in _ALL_CASES:
        stem = hostile.case_id(case)
        header = (out / f"{stem}.csv").read_text().splitlines()[0]
        assert header == "shift_cm-1,intensity"
        truth = json.loads((out / f"{stem}_truth.json").read_text())
        assert truth["case_id"] == stem
        assert _REQUIRED_TRUTH_KEYS <= set(truth)
        assert "seed" in truth


def test_manifest_lists_every_case(tmp_path):
    """The manifest has one row per case with both ratios for the pairing audit."""
    import pandas as pd

    out = hostile.suite(tmp_path)
    man = pd.read_csv(out / "manifest.csv")
    assert len(man) == 90
    assert set(man["case_id"]) == {hostile.case_id(c) for c in _ALL_CASES}
    for col in ("true_id_ig_area", "true_id_ig_height", "severity", "csv", "truth_json"):
        assert col in man.columns


# --------------------------------------------------------------------------- #
# Scope guards: Tier-A untouched, no Day-5 scope added
# --------------------------------------------------------------------------- #
def _dir_digest(d: Path) -> dict:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(d.iterdir())
        if p.is_file()
    }


def test_tierA_untouched_by_tierB_suite(tmp_path):
    """Generating the Tier-B suite does not modify any committed Tier-A file."""
    if not _TIERA.is_dir():
        pytest.skip("committed Tier-A suite not present")
    before = _dir_digest(_TIERA)
    # Expect the committed Tier-A counts unchanged (50 CSV + 50 truth + manifest).
    n_csv = len([n for n in before if n.endswith(".csv") and n != "manifest.csv"])
    n_json = len([n for n in before if n.endswith("_truth.json")])
    assert n_csv == 50 and n_json == 50

    hostile.suite(tmp_path)  # writes only under tmp_path

    after = _dir_digest(_TIERA)
    assert before == after, "Tier-A contents changed while building Tier-B"


_DAY5_STUBS = ["mdc", "reporting", "selectors", "viz"]


def test_no_day5_scope_added():
    """The Day-5 module stubs remain stubs and hostile pulls in no Day-5 code."""
    for name in _DAY5_STUBS:
        text = (_SRC / f"{name}.py").read_text()
        assert "def " not in text and "class " not in text, (
            f"Day-5 stub {name}.py gained implementation"
        )
    src = (_SRC / "hostile.py").read_text()
    for name in _DAY5_STUBS:
        assert f"import {name}" not in src and f"from .{name}" not in src
