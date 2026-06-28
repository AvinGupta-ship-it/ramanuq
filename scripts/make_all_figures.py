"""Deterministically regenerate all project figures (F1-F9).

Determinism contract:

- Agg backend, one fixed ``SEED``, no embedded timestamps. PNG/PDF metadata is
  stripped and ``SOURCE_DATE_EPOCH`` is pinned (for a fixed PDF creation date)
  in :func:`ramanuq.viz.save_figure`. Two consecutive runs therefore produce
  byte-identical files.
- F8 reproduces the digitized published spectra described by
  ``data/digitized/provenance.yaml``; all nine figures (F1-F9) are generated.

Run: ``python3 scripts/make_all_figures.py``.
"""

from __future__ import annotations

import hashlib
import os
import sys

import matplotlib  # noqa: E402

matplotlib.use("Agg")

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from ramanuq import viz  # noqa: E402
from ramanuq.reporting import write_report_data  # noqa: E402
from ramanuq.synth import SEED  # noqa: E402

#: The fixed project seed governs every stochastic element in the figures.
FIGURE_SEED = int(SEED)

OUT_DIR = os.path.join(_REPO_ROOT, "figures")
#: All figures are generated; F8 reads digitized spectra from
#: data/digitized/ (raises if the provenance/CSVs are absent).
GENERATED = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"]
DEFERRED = []


def _seed_everything():
    import random

    import numpy as np

    random.seed(FIGURE_SEED)
    np.random.seed(FIGURE_SEED)


def _digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build_all(out_dir=OUT_DIR, refresh_report=True):
    """Render all figures deterministically; return the list of written paths."""
    os.makedirs(out_dir, exist_ok=True)
    viz.apply_style()
    if refresh_report:
        # Recompute report_data.json (self-check enforced) so figures cite the
        # code's numbers, not stale ones.
        write_report_data()
    df = viz.load_study()
    report = viz.load_report()

    written = []
    for name in GENERATED:
        _seed_everything()
        paths = viz.render_figure(name, df, report, out_dir,
                                  dpi=viz._STYLE["savefig.dpi"])
        written.extend(paths)
        print(f"  generated {name}: "
              f"{', '.join(os.path.basename(p) for p in paths)}")
    for name in DEFERRED:
        print(f"  skipped {name}: deferred (no digitized data; F8 joins Day 10)")
    return written


def main():
    print("Run 1 — generating figures ...")
    written = build_all()
    digests1 = {p: _digest(p) for p in written}

    print("Run 2 — regenerating to verify byte-identity ...")
    build_all()
    digests2 = {p: _digest(p) for p in written}

    identical = all(digests1[p] == digests2[p] for p in written)
    print()
    print("Byte-identity check across two consecutive runs:")
    for p in written:
        ok = digests1[p] == digests2[p]
        print(f"  [{'OK ' if ok else 'DIFF'}] {os.path.basename(p)}")
    print()
    if identical:
        print(f"BYTE-IDENTICAL: all {len(written)} files matched across two runs.")
    else:
        print("NOT byte-identical: see DIFF entries above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
