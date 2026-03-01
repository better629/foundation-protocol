#!/usr/bin/env bash
set -euo pipefail

PYTHON_CMD="${PYTHON_CMD:-python3}"

PYTHONPATH=src "$PYTHON_CMD" -m examples.quickstart.basic_flow >/dev/null
PYTHONPATH=src "$PYTHON_CMD" -m examples.scenarios.llm_tool_collaboration >/dev/null
PYTHONPATH=src "$PYTHON_CMD" -m examples.scenarios.governed_transfer >/dev/null
PYTHONPATH=src "$PYTHON_CMD" -m examples.scenarios.economy_settlement >/dev/null
PYTHONPATH=src "$PYTHON_CMD" -m examples.scenarios.transport_jsonrpc >/dev/null
PYTHONPATH=src "$PYTHON_CMD" -m examples.scenarios.federated_discovery_trade >/dev/null
