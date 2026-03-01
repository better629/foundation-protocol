# Getting Started

## Requirements

- Python `>=3.10`

## Install

From repository root:

```bash
python3 -m pip install -e .
```

For development and documentation:

```bash
python3 -m pip install -e ".[dev,docs]"
```

## Run tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -q
```

## Minimal runtime example

```python
from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind

server = FPServer()
server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))

session = server.sessions_create(
    participants={"fp:agent:planner", "fp:tool:weather"},
    roles={
        "fp:agent:planner": {"coordinator"},
        "fp:tool:weather": {"provider"},
    },
)

server.register_operation(
    "weather.lookup",
    lambda payload: {"city": payload["city"], "temp_c": 23},
)

activity = server.activities_start(
    session_id=session.session_id,
    owner_entity_id="fp:tool:weather",
    initiator_entity_id="fp:agent:planner",
    operation="weather.lookup",
    input_payload={"city": "San Francisco"},
)

print(activity.state.value)
```

## Event streaming

```python
stream = server.events_stream(session_id=session.session_id)
events = server.events_read(stream_id=stream["stream_id"], limit=100)
server.events_ack(stream_id=stream["stream_id"], event_ids=[e.event_id for e in events])
```
