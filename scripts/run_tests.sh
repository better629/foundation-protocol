#!/usr/bin/env bash
set -euo pipefail

PYTHON_CMD="${PYTHON_CMD:-python3}"

PYTHONPATH=src "$PYTHON_CMD" -m pytest -q
