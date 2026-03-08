from __future__ import annotations

import json
from pathlib import Path

from fp_skill.cli import main


ROOT = Path(__file__).resolve().parents[2]


def test_cli_validate_manifest() -> None:
    rc = main(["validate", str(ROOT / "skills/examples/weather.skill.json")])
    assert rc == 0


def test_cli_smoke_manifest() -> None:
    rc = main(
        [
            "smoke",
            str(ROOT / "skills/examples/weather.skill.json"),
            "--operation",
            "weather.lookup",
            "--payload",
            '{"city":"Tokyo"}',
            "--idempotency-key",
            "idem-cli-weather-001",
        ]
    )
    assert rc == 0


def test_cli_serve_manifest_with_announce_file(tmp_path: Path) -> None:
    announce = tmp_path / "serve.json"
    rc = main(
        [
            "serve",
            str(ROOT / "skills/examples/weather.skill.json"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--duration-seconds",
            "0.1",
            "--announce-file",
            str(announce),
            "--directory",
            "inmemory",
        ]
    )
    assert rc == 0
    data = json.loads(announce.read_text(encoding="utf-8"))
    assert data["self_check"]["ping_ok"] is True
    assert data["server_card"]["entity_id"] == "fp:agent:weather-bot"
    assert data["directory"]["mode"] == "inmemory"
