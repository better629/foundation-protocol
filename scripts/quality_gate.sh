#!/usr/bin/env bash
set -euo pipefail

PYTHON_CMD="${PYTHON_CMD:-python3}"

PYTHON_CMD="$PYTHON_CMD" bash scripts/run_tests.sh
PYTHON_CMD="$PYTHON_CMD" bash scripts/run_examples.sh
"$PYTHON_CMD" -m compileall -q src tests examples scripts
"$PYTHON_CMD" scripts/validate_specs.py
