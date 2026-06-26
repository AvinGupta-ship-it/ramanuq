#!/usr/bin/env bash
# repro.sh - reproduce RamanUQ figures and report numbers from the committed study results.
# Default: fast path - recompute report_data + figures from the committed parquet and diff vs committed.
# Opt-in: RUN_FULL_STUDY=1 regenerates the ~7-hour Tier-B crossed study parquet first (NOT needed for reproduction).
set -euo pipefail

# 1) Isolated environment: reuse an existing .venv, else build a fresh one (simulates a clean clone).
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e .

# 2) (Optional) regenerate the full study parquet (~7h). Off by default.
if [[ "${RUN_FULL_STUDY:-0}" == "1" ]]; then
  echo "RUN_FULL_STUDY=1 - regenerating the Tier-B crossed study (~7h)..."
  python3 -c "from ramanuq.grid import run_study; run_study()"
fi

# 3) Recompute every reported number from the committed parquet.
python3 -c "from ramanuq.reporting import write_report_data; write_report_data()"

# 4) Regenerate all figures (deterministic, byte-stable) and rebuild the report.
python3 scripts/make_all_figures.py
python3 scripts/build_report.py

# 5) Figure QA.
python3 scripts/figure_qa.py

# 6) Diff regenerated outputs vs committed. The report PDF embeds a build timestamp and cannot be
#    byte-diffed, so we diff its byte-stable inputs instead (report_data.json + report_draft.md + figures).
echo "=== Diff: report_data.json + report_draft.md + figures (must be empty for a byte-identical reproduction) ==="
git diff --stat -- docs/report_data.json docs/report_draft.md figures/
echo "=== Done. Empty diff above = numbers and figures reproduced byte-for-byte. ==="
