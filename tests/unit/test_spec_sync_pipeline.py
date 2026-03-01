from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_spec_sync import check_sync  # noqa: E402
from spec_sync_lib import build_manifest, write_outputs  # noqa: E402


class SpecSyncPipelineTests(unittest.TestCase):
    def test_check_detects_drift_and_passes_when_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core = root / "fp-core.schema.json"
            openrpc = root / "fp-openrpc.json"
            generated_py = root / "spec_manifest.py"
            generated_json = root / "spec-sync-manifest.json"

            core.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "$defs": {
                            "Entity": {"type": "object"},
                            "Session": {"type": "object"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            openrpc.write_text(
                json.dumps(
                    {
                        "openrpc": "1.3.2",
                        "info": {"title": "x", "version": "0.1.0"},
                        "methods": [
                            {"name": "fp/ping", "params": [], "result": {"name": "result", "schema": {"type": "object"}}}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            manifest = build_manifest(core, openrpc)
            write_outputs(manifest, output_py=generated_py, output_json=generated_json)

            ok, messages = check_sync(
                core_path=core,
                openrpc_path=openrpc,
                generated_py_path=generated_py,
                manifest_json_path=generated_json,
            )
            self.assertTrue(ok)
            self.assertEqual(messages, [])

            generated_py.write_text("# drift\n", encoding="utf-8")
            ok, messages = check_sync(
                core_path=core,
                openrpc_path=openrpc,
                generated_py_path=generated_py,
                manifest_json_path=generated_json,
            )
            self.assertFalse(ok)
            self.assertTrue(any("drift detected" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
