from __future__ import annotations

from pathlib import Path

import pytest

from fp_skill.manifest import SkillManifest, SkillManifestError, load_manifest


ROOT = Path(__file__).resolve().parents[2]


def test_load_example_manifest() -> None:
    manifest = load_manifest(ROOT / "skills/examples/weather.skill.json")
    assert manifest.skill_spec_version == "0.1"
    assert manifest.entity.entity_id == "fp:agent:weather-bot"
    assert manifest.connection.mode == "inproc"
    assert manifest.operations[0].name == "weather.lookup"


def test_manifest_rejects_duplicate_operation_names() -> None:
    raw = {
        "skill_spec_version": "0.1",
        "fp_version": "0.1.0",
        "entity": {
            "entity_id": "fp:agent:test",
            "kind": "agent",
            "capability_purpose": ["x"],
        },
        "connection": {"mode": "inproc"},
        "auth": {"mode": "none"},
        "defaults": {"auto_session": True},
        "operations": [
            {"name": "op", "handler": "skills.examples.weather_handlers:lookup_weather"},
            {"name": "op", "handler": "skills.examples.weather_handlers:lookup_weather"},
        ],
    }
    with pytest.raises(SkillManifestError, match="duplicate operation name"):
        SkillManifest.from_dict(raw)
