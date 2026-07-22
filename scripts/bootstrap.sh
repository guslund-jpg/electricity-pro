#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_COMMAND="${PYTHON_COMMAND:-python3}"

cd "${PROJECT_ROOT}"

if ! command -v "${PYTHON_COMMAND}" >/dev/null 2>&1; then
  echo "Error: ${PYTHON_COMMAND} was not found."
  echo "Install Python 3 and run this script again."
  exit 1
fi

if [[ -d "${VENV_DIR}" ]]; then
  VENV_PYTHON="${VENV_DIR}/bin/python"

  if [[ ! -x "${VENV_PYTHON}" ]] ||
     ! "${VENV_PYTHON}" -c 'import sys' >/dev/null 2>&1; then
    echo "Removing an invalid or relocated virtual environment."
    rm -rf "${VENV_DIR}"
  fi
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating Python virtual environment."
  "${PYTHON_COMMAND}" -m venv "${VENV_DIR}"
fi

echo "Installing development dependencies."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r requirements-dev.txt

echo "Installing pre-commit hooks."
"${VENV_DIR}/bin/pre-commit" install

echo
echo "Development environment ready."
echo "Activate it with:"
echo "  source .venv/bin/activate"
echo
echo "Then validate the repository with:"
echo "  ./scripts/validate.sh"
