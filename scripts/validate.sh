#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="${PROJECT_ROOT}/.venv/bin"

cd "${PROJECT_ROOT}"

if [[ -x "${VENV_BIN}/yamllint" ]]; then
  YAMLLINT="${VENV_BIN}/yamllint"
elif command -v yamllint >/dev/null 2>&1; then
  YAMLLINT="$(command -v yamllint)"
else
  echo "Error: yamllint is not installed."
  echo "Run ./scripts/bootstrap.sh and try again."
  exit 1
fi

if [[ -x "${VENV_BIN}/python" ]]; then
  PYTHON="${VENV_BIN}/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "Error: Python 3 is not installed."
  exit 1
fi

echo "Running YAML validation."
"${YAMLLINT}" .

if [[ -f scripts/check_duplicate_unique_ids.py ]]; then
  echo "Checking for duplicate unique IDs."
  "${PYTHON}" scripts/check_duplicate_unique_ids.py
fi

if [[ -f scripts/check_repository_policy.py ]]; then
  echo "Checking repository policies."
  "${PYTHON}" scripts/check_repository_policy.py
fi

echo "Checking Git whitespace."
git diff --check

echo "All validation checks passed."
