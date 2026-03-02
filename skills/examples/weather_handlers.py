"""Example handlers for FP Skill runtime demos."""

from __future__ import annotations

from fp_skill.decorators import fp_operation


@fp_operation("weather.lookup")
def lookup_weather(payload: dict[str, object]) -> dict[str, object]:
    city = str(payload.get("city", "unknown"))
    return {
        "city": city,
        "condition": "sunny",
        "temp_c": 22,
    }
