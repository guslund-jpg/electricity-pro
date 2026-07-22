#!/usr/bin/env sh
set -eu
yamllint .
python3 scripts/check_unique_ids.py packages dashboards config
python3 scripts/check_repository.py
echo "Static validation passed."
