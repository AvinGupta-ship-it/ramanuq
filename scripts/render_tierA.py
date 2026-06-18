"""Render representative Tier-A synthetic spectra to PNG (human realism gate).

Deterministic (Agg backend, fixed project SEED, no timestamps).  Renders one
stage-1 case (area ratio 1.0, noiseless) and one stage-2 case (noiseless) so the
mixed Lorentzian/Gaussian band structure is visible.  Prints the exact output
paths.  This script makes NO realism judgement -- it only produces the figures a
human inspects.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, deterministic
import matplotlib.pyplot as plt  # noqa: E402

from ramanuq import synth  # noqa: E402

_OUT_DIR = Path("data/synthetic/tierA/figures")


def _family_label(truth) -> str:
    """Compact per-band family description, e.g. 'D,G,Dprime: lorentzian'."""
    parts = [f"{p['name']}({p['lineshape'][:4]})" for p in truth["peaks"]]
    return " + ".join(parts)


def _render(case: synth.Case, out_path: Path) -> Path:
    spec, truth = synth.generate(case)
    noise = "noiseless" if truth["snr_label"] is None else f"SNR {truth['snr_label']}"

    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    ax.plot(spec.shift, spec.intensity, color="C0", lw=1.2)
    ax.set_xlabel("Raman shift (cm$^{-1}$)")
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_title(
        f"{truth['case_id']}  |  stage {truth['stage']}, {noise}\n"
        f"peak set: {_family_label(truth)}"
    )
    ax.text(
        0.98,
        0.95,
        f"true $I_D/I_G$ (area) = {truth['true_id_ig_area']:.3g}",
        transform=ax.transAxes,
        ha="right",
        va="top",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    stage1 = synth.Case(1, 1.0, "none", None, spike=False, recovery=True)
    stage2 = synth.Case(2, synth.STAGE2_RATIO, "none", None, spike=False, recovery=True)

    p1 = _render(stage1, _OUT_DIR / "tierA_stage1_r1p0_noiseless.png")
    p2 = _render(stage2, _OUT_DIR / "tierA_stage2_r1p0_noiseless.png")

    print("Tier-A realism plots written:")
    print(f"  stage-1 (area ratio 1.0, noiseless): {p1.resolve()}")
    print(f"  stage-2 (noiseless):                 {p2.resolve()}")


if __name__ == "__main__":
    main()
