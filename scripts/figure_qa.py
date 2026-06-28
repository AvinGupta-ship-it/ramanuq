"""Quality-assurance harness for the project figures (F1-F9).

Per figure, this harness asserts:

1. the on-disk PNG and PDF exist in ``figures/`` and exceed a size threshold;
2. the figure carries axis labels where it has data axes, plus an explanatory
   element (legend / colorbar / table / annotation) appropriate to its kind;
3. two consecutive in-memory renders are byte-identical (determinism).

F8 reproduces the digitized published spectra in ``data/digitized/`` (Gate V5)
and is QA'd alongside the rest; its per-panel titles carry the published I_D/I_G.

Run: ``python3 scripts/figure_qa.py``  (exits non-zero on any failure).
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from ramanuq import viz  # noqa: E402

FIG_DIR = os.path.join(_REPO_ROOT, "figures")
PNG_MIN_BYTES = 20_000
PDF_MIN_BYTES = 10_000

# Per-figure expectations. ``explain`` names the explanatory element a figure of
# that kind carries instead of (or in addition to) a legend.
#   legend  -> at least one axes has a legend
#   colorbar-> the figure has a colorbar axes
#   table   -> the axes holds a matplotlib table
#   text    -> the axes carries an annotation/text box
#   title   -> the axes carries a panel title (e.g. F8's I_D/I_G labels)
FIG_SPEC = {
    "F1": {"labels": True, "explain": "legend"},
    "F2": {"labels": True, "explain": "legend"},
    "F3": {"labels": True, "explain": "colorbar"},
    "F4": {"labels": True, "explain": "colorbar"},
    "F5": {"labels": True, "explain": "legend"},
    "F6": {"labels": False, "explain": "table"},
    "F7": {"labels": True, "explain": "legend"},
    "F8": {"labels": True, "explain": "title"},
    "F9": {"labels": True, "explain": "text"},
    "F10": {"labels": True, "explain": "legend"},
}
DEFERRED = []


def _digest_bytes(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _has_labels(fig):
    for ax in fig.axes:
        if ax.get_xlabel().strip() and ax.get_ylabel().strip():
            return True
    return False


def _has_legend(fig):
    return any(ax.get_legend() is not None for ax in fig.axes)


def _has_colorbar(fig):
    # A colorbar lives on its own axes whose label or a mappable is set.
    return any(getattr(ax, "_colorbar", None) is not None for ax in fig.axes) or \
        len(fig.axes) > 0 and any(
            ax.get_label() == "<colorbar>" for ax in fig.axes
        )


def _has_table(fig):
    return any(len(ax.tables) > 0 for ax in fig.axes)


def _has_text(fig):
    for ax in fig.axes:
        if any(t.get_text().strip() for t in ax.texts):
            return True
    return False


def _has_title(fig):
    return any(ax.get_title().strip() for ax in fig.axes)


def _explain_present(fig, kind):
    return {
        "legend": _has_legend,
        "colorbar": _has_colorbar,
        "table": _has_table,
        "text": _has_text,
        "title": _has_title,
    }[kind](fig)


def qa_one(name, spec, df, report):
    """Return (passed, messages) for one figure."""
    msgs = []
    ok = True

    png = os.path.join(FIG_DIR, f"{name}.png")
    pdf = os.path.join(FIG_DIR, f"{name}.pdf")
    for path, floor in ((png, PNG_MIN_BYTES), (pdf, PDF_MIN_BYTES)):
        if not os.path.exists(path):
            ok = False
            msgs.append(f"missing {os.path.basename(path)}")
        elif os.path.getsize(path) < floor:
            ok = False
            msgs.append(
                f"{os.path.basename(path)} too small "
                f"({os.path.getsize(path)} < {floor})"
            )

    # Render once to inspect structure (labels / explanatory element).
    fig = viz.FIGURES[name](df, report)
    if spec["labels"] and not _has_labels(fig):
        ok = False
        msgs.append("missing axis labels")
    if not _explain_present(fig, spec["explain"]):
        ok = False
        msgs.append(f"missing {spec['explain']}")
    plt.close(fig)

    # Byte-identity across two in-memory renders.
    with tempfile.TemporaryDirectory() as td:
        d1 = d2 = None
        f1 = viz.FIGURES[name](df, report)
        viz.save_figure(f1, os.path.join(td, "a"))
        plt.close(f1)
        f2 = viz.FIGURES[name](df, report)
        viz.save_figure(f2, os.path.join(td, "b"))
        plt.close(f2)
        for ext in ("png", "pdf"):
            d1 = _digest_bytes(os.path.join(td, f"a.{ext}"))
            d2 = _digest_bytes(os.path.join(td, f"b.{ext}"))
            if d1 != d2:
                ok = False
                msgs.append(f"{ext} not byte-identical across renders")

    return ok, msgs


def main():
    viz.apply_style()
    df = viz.load_study()
    report = viz.load_report()

    print("Figure QA harness")
    print("=" * 52)
    all_ok = True
    for name, spec in FIG_SPEC.items():
        ok, msgs = qa_one(name, spec, df, report)
        all_ok = all_ok and ok
        status = "PASS" if ok else "FAIL"
        detail = "" if ok else "  (" + "; ".join(msgs) + ")"
        print(f"  [{status}] {name}{detail}")
    for name in DEFERRED:
        print(f"  [DEFERRED] {name} — no digitized data; joins green set on Day 10")
    print("=" * 52)
    if all_ok:
        print(f"All {len(FIG_SPEC)} generated figures PASS QA.")
    else:
        print("QA FAILURES present (see above).")
        sys.exit(1)


if __name__ == "__main__":
    main()
