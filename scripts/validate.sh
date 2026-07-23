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
"${YAMLLINT}" \
  .github \
  config \
  dashboards \
  packages \
  custom_components

echo "Checking repository policies."
"${PYTHON}" scripts/check_repository.py

echo "Checking for duplicate unique IDs."
"${PYTHON}" scripts/check_unique_ids.py packages dashboards config

echo "Checking JSON files."
while IFS= read -r -d '' json_file; do
  "${PYTHON}" -m json.tool "${json_file}" >/dev/null
done < <(
  find . \
    -path './.git' -prune -o \
    -path './.venv' -prune -o \
    -name '*.json' -type f -print0
)

echo "Checking Python syntax."
if [[ -d custom_components ]]; then
  while IFS= read -r -d '' python_file; do
    "${PYTHON}" -m py_compile "${python_file}"
  done < <(
    find custom_components \
      -name '*.py' \
      -type f \
      -print0
  )
fi

echo "Checking Git whitespace."
git diff --check

echo "All validation checks passed."
