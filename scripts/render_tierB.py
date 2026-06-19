"""Render representative Tier-B (hostile) synthetic spectra to PNG (realism gate).

Deterministic (Agg backend, fixed project SEED, no timestamps).  Renders four
*representative* Tier-B cases spanning both stages, all three baseline severities,
and the SNR range so the human realism gate sees variety, not four near-identical
spectra.  Each figure shows the full observed spectrum (baseline + noise), the
baseline-free generator band components (dashed), and the added baseline, with
labelled axes and an annotation of the case id and generator families.

This script makes NO realism judgement -- it only produces the figures a human
inspects.  It prints the exact output paths.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, deterministic
import matplotlib.pyplot as plt  # noqa: E402

from ramanuq import hostile  # noqa: E402

_OUT_DIR = Path("data/synthetic/tierB/figures")

# Four representative cells: vary stage, baseline severity, and SNR.
_CASES = [
    hostile.Case(1, "none", 200, 0),
    hostile.Case(1, "strong", 15, 2),
    hostile.Case(2, "mild", 50, 1),
    hostile.Case(2, "strong", 15, 3),
]


def _render(case: hostile.Case, out_path: Path) -> Path:
    built = hostile.assemble(case)
    truth = built.truth
    x = built.x

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    # Full observed spectrum (baseline + noise).
    ax.plot(x, built.observed, color="0.25", lw=1.0, label="observed (baseline+noise)")
    # Added baseline.
    ax.plot(x, built.baseline, color="C3", lw=1.4, ls="-", label="added baseline")
    # Baseline-free generator band components (dashed).
    for name, comp in built.components.items():
        ax.plot(x, comp, lw=1.1, ls="--", label=f"{name} (band)")

    ax.set_xlabel("Raman shift (cm$^{-1}$)")
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_title(
        f"{truth['case_id']}  |  stage {truth['stage']}, "
        f"baseline {truth['severity']}, SNR {truth['snr_label']}\n"
        f"families: {', '.join(truth['generator_families'])}"
    )
    ax.text(
        0.98,
        0.95,
        f"true $I_D/I_G$ area={truth['true_id_ig_area']:.3g}, "
        f"height={truth['true_id_ig_height']:.3g}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
    )
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Tier-B realism plots written:")
    for case in _CASES:
        path = _OUT_DIR / f"{hostile.case_id(case)}.png"
        _render(case, path)
        print(f"  {path.resolve()}")


if __name__ == "__main__":
    main()
