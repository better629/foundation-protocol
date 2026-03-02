# FP Skills (Monorepo Isolated Layer)

This directory contains the FP Skill layer, intentionally isolated from `src/fp` core runtime.

## Design rules

- Skills depend on FP protocol/runtime APIs.
- FP core does not depend on skills.
- Manifest-driven bootstrap is the default integration path.

## Structure

```text
skills/
  spec/
    manifest.schema.json
    manifest-v0.1.md
  examples/
    weather.skill.json
    weather_handlers.py
  python/
    fp_skill/
      manifest.py
      runtime.py
      decorators.py
      cli.py
```

## Quick start

Validate manifest:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill validate skills/examples/weather.skill.json
```

Smoke bootstrap and local invoke:

```bash
PYTHONPATH=src:skills/python python3 -m fp_skill smoke skills/examples/weather.skill.json \
  --operation weather.lookup --payload '{"city":"Paris"}'
```

## Why this exists

Skill layer reduces FP adoption friction:

- auto-load entity + operation metadata from manifest
- auto-register entity and operations
- auto-create governed session (when enabled)
- keep protocol semantics in FP core unchanged
