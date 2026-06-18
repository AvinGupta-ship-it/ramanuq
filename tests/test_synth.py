"""Tests for the Tier-A synthetic generator and suite (:mod:`ramanuq.synth`).

These check the *generator contract* independently of the fitter: determinism,
truth-schema completeness (both labelled ratios, all parameters, the seed),
finiteness, a strictly increasing Raman-shift axis, unique filenames, one-to-one
CSV/JSON pairing, generator parameters inside the model's bounds, and presence of
every required suite case.  Recovery (Gate V1) lives in ``test_fit_recovery.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ramanuq import synth
from ramanuq.model import build_model

#: Committed Tier-A suite, located relative to this file so the check is
#: path-independent (passes in CI on Linux just as locally).
_COMMITTED_TIERA = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "tierA"

# Restated model bounds (centers within +/-40 of anchor; FWHM ranges).  Restated
# rather than imported so the test fails if the model drifts.
_ANCHORS = {"D": 1350.0, "G": 1580.0, "Dprime": 1620.0, "D3": 1500.0, "D4": 1200.0}
_CENTER_WINDOW = 40.0
_FWHM_RANGE = {
    "D": (4.0, 300.0),
    "G": (4.0, 300.0),
    "Dprime": (4.0, 60.0),
    "D3": (4.0, 300.0),
    "D4": (4.0, 300.0),
}

_ALL_CASES = synth.enumerate_cases()


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "case",
    [
        synth.Case(1, 1.0, "none", None, False, True),  # noise-free
        synth.Case(1, 0.5, "strong_curved", 15, False, False),  # noisy
        synth.Case(2, 1.0, "mild_cubic", 50, True, False),  # noisy + spikes
    ],
)
def test_same_seed_reproduces_arrays_and_truth(case):
    """Same seed -> numerically identical spectrum and truth."""
    s1, t1 = synth.generate(case, seed=synth.SEED)
    s2, t2 = synth.generate(case, seed=synth.SEED)
    assert np.array_equal(s1.shift, s2.shift)
    assert np.array_equal(s1.intensity, s2.intensity)
    assert t1 == t2


def test_different_seed_changes_noisy_spectrum_only_via_noise():
    """A different seed changes a noisy draw but not the noiseless signal grid."""
    case = synth.Case(1, 1.0, "none", 50, False, False)
    s1, _ = synth.generate(case, seed=synth.SEED)
    s2, _ = synth.generate(case, seed=synth.SEED + 1)
    assert np.array_equal(s1.shift, s2.shift)
    assert not np.array_equal(s1.intensity, s2.intensity)


# --------------------------------------------------------------------------- #
# Truth-schema completeness
# --------------------------------------------------------------------------- #
_REQUIRED_TRUTH_KEYS = {
    "case_id",
    "stage",
    "recovery",
    "seed",
    "wavelength_nm",
    "grid",
    "baseline_label",
    "snr_label",
    "spike",
    "id_ig_area_ratio_nominal",
    "peaks",
    "true_id_ig_area",
    "true_id_ig_height",
}
_REQUIRED_PEAK_KEYS = {"name", "center", "fwhm", "area", "height", "lineshape", "stage"}


@pytest.mark.parametrize("case", _ALL_CASES, ids=synth.case_id)
def test_truth_schema_complete(case):
    """Every truth record carries both ratios, the seed, and all per-peak params."""
    _, truth = synth.generate(case)

    assert _REQUIRED_TRUTH_KEYS <= set(truth), (
        f"missing truth keys: {_REQUIRED_TRUTH_KEYS - set(truth)}"
    )
    # Both ratios present, labelled, finite, positive.
    assert "true_id_ig_area" in truth and "true_id_ig_height" in truth
    assert np.isfinite(truth["true_id_ig_area"]) and truth["true_id_ig_area"] > 0
    assert np.isfinite(truth["true_id_ig_height"]) and truth["true_id_ig_height"] > 0
    # Seed recorded.
    assert truth["seed"] == synth.SEED
    # Grid fully described.
    assert {"min", "max", "step"} <= set(truth["grid"])
    # Every peak carries center/fwhm/area/height/lineshape/stage.
    assert truth["peaks"]
    for peak in truth["peaks"]:
        assert _REQUIRED_PEAK_KEYS <= set(peak), (
            f"missing peak keys: {_REQUIRED_PEAK_KEYS - set(peak)}"
        )


@pytest.mark.parametrize("case", _ALL_CASES, ids=synth.case_id)
def test_truth_ratios_match_analytic_definition(case):
    """Stored ratios equal the analytic area/height ratios of the D and G bands."""
    _, truth = synth.generate(case)
    peaks = {p["name"]: p for p in truth["peaks"]}
    d, g = peaks["D"], peaks["G"]
    assert truth["true_id_ig_area"] == pytest.approx(d["area"] / g["area"])
    assert truth["true_id_ig_height"] == pytest.approx(d["height"] / g["height"])
    # Area ratio matches the nominal swept value.
    assert truth["true_id_ig_area"] == pytest.approx(truth["id_ig_area_ratio_nominal"])


# --------------------------------------------------------------------------- #
# Spectrum integrity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _ALL_CASES, ids=synth.case_id)
def test_spectrum_finite_and_axis_strictly_increasing(case):
    """Finite values; strictly increasing Raman-shift axis at the contracted step."""
    spec, truth = synth.generate(case)
    assert np.all(np.isfinite(spec.shift))
    assert np.all(np.isfinite(spec.intensity))
    diffs = np.diff(spec.shift)
    assert np.all(diffs > 0)  # strictly increasing
    assert np.allclose(diffs, truth["grid"]["step"])
    assert spec.shift[0] == pytest.approx(truth["grid"]["min"])
    assert spec.shift[-1] == pytest.approx(truth["grid"]["max"])


# --------------------------------------------------------------------------- #
# Generator parameters inside model bounds
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _ALL_CASES, ids=synth.case_id)
def test_generator_params_within_model_bounds(case):
    """Centers within +/-40 of anchor; FWHM in range; areas non-negative."""
    _, truth = synth.generate(case)
    for peak in truth["peaks"]:
        name = peak["name"]
        anchor = _ANCHORS[name]
        assert anchor - _CENTER_WINDOW <= peak["center"] <= anchor + _CENTER_WINDOW
        lo, hi = _FWHM_RANGE[name]
        assert lo <= peak["fwhm"] <= hi
        assert peak["area"] >= 0.0


def test_generator_centers_reachable_by_matched_model():
    """Each generator center lies within the matched model's center bounds."""
    for case in synth.recovery_cases():
        _, truth = synth.generate(case)
        peak_set = "DGDp" if case.stage == 1 else "DGDpD3D4"
        params = build_model(peak_set, "lorentzian").make_params()
        for peak in truth["peaks"]:
            c = params[f"{peak['name']}_center"]
            assert c.min <= peak["center"] <= c.max
            f = params[f"{peak['name']}_fwhm"]
            assert f.min <= peak["fwhm"] <= f.max


# --------------------------------------------------------------------------- #
# Suite-level: naming, pairing, coverage
# --------------------------------------------------------------------------- #
def test_case_ids_unique_and_valid():
    """All 50 case_ids are unique, non-empty, and filesystem-safe."""
    ids = [synth.case_id(c) for c in _ALL_CASES]
    assert len(ids) == len(set(ids))
    for cid in ids:
        assert cid
        assert all(ch.isalnum() or ch in "_-" for ch in cid)


def test_suite_writes_one_to_one_csv_json_pairs(tmp_path):
    """suite() writes exactly one CSV and one matching *_truth.json per case."""
    out = synth.suite(tmp_path)
    csvs = sorted(p.stem for p in out.glob("*.csv") if p.name != "manifest.csv")
    jsons = sorted(p.name[: -len("_truth.json")] for p in out.glob("*_truth.json"))
    assert len(csvs) == len(_ALL_CASES)
    assert csvs == jsons  # exact one-to-one pairing by stem
    assert (out / "manifest.csv").exists()


def test_suite_csv_schema_and_truth_loadable(tmp_path):
    """CSVs use the contracted columns; each truth JSON is valid and complete."""
    out = synth.suite(tmp_path)
    for case in _ALL_CASES:
        stem = synth.case_id(case)
        header = (out / f"{stem}.csv").read_text().splitlines()[0]
        assert header == "shift_cm-1,intensity"
        truth = json.loads((out / f"{stem}_truth.json").read_text())
        assert truth["case_id"] == stem
        assert _REQUIRED_TRUTH_KEYS <= set(truth)


def test_manifest_lists_every_case(tmp_path):
    """The manifest has one row per case with both ratios for the pairing audit."""
    import pandas as pd

    out = synth.suite(tmp_path)
    man = pd.read_csv(out / "manifest.csv")
    assert len(man) == len(_ALL_CASES)
    assert set(man["case_id"]) == {synth.case_id(c) for c in _ALL_CASES}
    for col in ("true_id_ig_area", "true_id_ig_height", "csv", "truth_json"):
        assert col in man.columns


def test_required_suite_dimensions_present():
    """Every required stage/ratio/baseline/SNR combination is generated."""
    recovery = [c for c in _ALL_CASES if c.recovery]
    noisy = [c for c in _ALL_CASES if not c.recovery]

    # Recovery: stage-1 x 4 ratios + stage-2 x 1.
    assert {(c.stage, c.ratio) for c in recovery} == {
        (1, 0.1), (1, 0.5), (1, 1.0), (1, 2.0), (2, 1.0)
    }

    # Stage-1 noisy factorial: ratio(4) x baseline(3) x SNR(3) = 36.
    s1 = [c for c in noisy if c.stage == 1]
    assert len(s1) == 36
    assert {c.ratio for c in s1} == set(synth.STAGE1_RATIOS)
    assert {c.baseline_label for c in s1} == set(synth.BASELINE_LABELS)
    assert {c.snr_label for c in s1} == set(synth.SNR_LEVELS)

    # Stage-2 noisy factorial: baseline(3) x SNR(3) = 9, fixed ratio.
    s2 = [c for c in noisy if c.stage == 2]
    assert len(s2) == 9
    assert {c.ratio for c in s2} == {synth.STAGE2_RATIO}
    assert {c.baseline_label for c in s2} == set(synth.BASELINE_LABELS)
    assert {c.snr_label for c in s2} == set(synth.SNR_LEVELS)

    # Cosmic spikes are NOT crossed as a suite dimension.
    assert all(c.spike is False for c in _ALL_CASES)
    assert len(_ALL_CASES) == 50


# --------------------------------------------------------------------------- #
# Committed data cannot drift from the generator
# --------------------------------------------------------------------------- #
def test_committed_suite_matches_generator(tmp_path):
    """Regenerating the suite for SEED reproduces the committed Tier-A files.

    Guards against the committed ``data/synthetic/tierA/`` artefacts silently
    diverging from :mod:`ramanuq.synth`: every CSV must be numerically equal (to a
    tight float tolerance), every ``*_truth.json`` byte-for-content equal, the
    manifest equal, and the *set* of files identical (no orphans either way).
    """
    if not _COMMITTED_TIERA.is_dir():
        pytest.skip(f"committed Tier-A suite not found at {_COMMITTED_TIERA}")

    out = synth.suite(tmp_path, seed=synth.SEED)

    def _stems(d, suffix):
        return {p.name[: -len(suffix)] for p in d.glob(f"*{suffix}")}

    # Same set of CSVs and truth records on both sides -- no stale orphan files
    # committed, and nothing the generator now emits is missing.
    assert _stems(out, ".csv") == _stems(_COMMITTED_TIERA, ".csv")
    assert _stems(out, "_truth.json") == _stems(_COMMITTED_TIERA, "_truth.json")

    for case in _ALL_CASES:
        stem = synth.case_id(case)

        # Truth JSON: exact structural equality.
        regen_truth = json.loads((out / f"{stem}_truth.json").read_text())
        committed_truth = json.loads(
            (_COMMITTED_TIERA / f"{stem}_truth.json").read_text()
        )
        assert committed_truth == regen_truth, f"truth drift: {stem}"

        # CSV: numerically equal to a tight tolerance.
        regen_csv = pd.read_csv(out / f"{stem}.csv")
        committed_csv = pd.read_csv(_COMMITTED_TIERA / f"{stem}.csv")
        assert list(committed_csv.columns) == list(regen_csv.columns)
        for col in regen_csv.columns:
            np.testing.assert_allclose(
                committed_csv[col].to_numpy(),
                regen_csv[col].to_numpy(),
                rtol=1e-12,
                atol=1e-12,
                err_msg=f"CSV drift: {stem}:{col}",
            )

    # Manifest: identical (string columns exact, float columns to tolerance).
    regen_man = pd.read_csv(out / "manifest.csv")
    committed_man = pd.read_csv(_COMMITTED_TIERA / "manifest.csv")
    pd.testing.assert_frame_equal(
        committed_man, regen_man, check_exact=False, rtol=1e-12, atol=1e-12
    )
