#!/usr/bin/env bash
# Bootstrap the SIXSTRINGDEMON Python environment.
# Run from the project root: bash scripts/bootstrap.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "[sixstringdemon] Setting up virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "[sixstringdemon] Created venv at $VENV_DIR"
else
    echo "[sixstringdemon] Venv already exists, skipping creation"
fi

# Activate
source "$VENV_DIR/bin/activate"

echo "[sixstringdemon] Installing dependencies from requirements.txt..."
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_ROOT/requirements.txt"

echo ""
echo "[sixstringdemon] Sanity checks:"

# Verify each key package imports cleanly
python3 -c "import guitarpro; print('  ✓ PyGuitarPro', guitarpro.__version__ if hasattr(guitarpro, '__version__') else '(ok)')"
python3 -c "from importlib.metadata import version; print('  ✓ click', version('click'))"
python3 -c "from importlib.metadata import version; print('  ✓ rich', version('rich'))"
python3 -c "import pandas; print('  ✓ pandas', pandas.__version__)"
python3 -c "import numpy; print('  ✓ numpy', numpy.__version__)"
python3 -c "import sklearn; print('  ✓ scikit-learn', sklearn.__version__)"
python3 -c "from importlib.metadata import version; print('  ✓ librosa', version('librosa'))"
python3 -c "import boto3; print('  ✓ boto3', boto3.__version__)"
python3 -c "from importlib.metadata import version; print('  ✓ watchdog', version('watchdog'))"

echo ""
echo "[sixstringdemon] Bootstrap complete. Activate with:"
echo "  source .venv/bin/activate"
