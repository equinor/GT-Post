#!/usr/bin/env bash
# Quickstart helper for GT-Post (macOS / Linux)
# Creates a Python 3.11 venv, installs pixi, runs `pixi install`, and executes
# the sample preprocessing step using `tests/data/input.ini`.

set -euo pipefail

OUT_DIR=${1:-./tmp/gtpost_preprocess_out}
VENV_DIR=${VENV_DIR:-.venv}

echo "GT-Post quickstart"
echo "Output directory: ${OUT_DIR}"

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python not found on PATH. Please install Python 3.11, or adjust the script to use a different interpreter." >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating venv in ${VENV_DIR}..."
  python -m venv "${VENV_DIR}"
fi

echo "Activating venv..."
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Installing project environment with pixi (this may take a while)..."
pixi install

echo "Running sample preprocessing using input.ini -> ${OUT_DIR}"
mkdir -p "${OUT_DIR}"
pixi run -- python -m gtpost.interface.preprocess "/Users/wilhelm.vold/Documents/gt-post/GT-Post/tests/data/input.ini" "${OUT_DIR}"

echo "Preprocessing finished. Listing output folder contents:"
ls -al "${OUT_DIR}"

echo "Tip: to run processing or postprocessing against an input folder, use:"
echo "  pixi run -- python -m gtpost.interface.process /path/to/input /path/to/output"
echo "  pixi run -- python -m gtpost.interface.postprocess /path/to/input /path/to/output"

echo "Done."
