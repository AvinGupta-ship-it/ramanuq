#!/usr/bin/env bash
# bootstrap.sh - create the venv, install RamanUQ editable, print a verification block.
set -euo pipefail
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e .
echo "=== Verification ==="
python3 -c "import sys; print('python:', sys.version.split()[0]); print('executable:', sys.executable)"
python3 -c "import numpy, scipy, lmfit, matplotlib, pandas, pyarrow; print('key packages import OK')"
python3 -c "import ramanuq; print('ramanuq import OK')"
