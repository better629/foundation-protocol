"""Minimal FP flow example."""

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


def main() -> None:
    server = FPServer()
    server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))

    server.register_operation("weather.lookup", lambda payload: {"city": payload["city"], "temp_c": 23})

    session = server.sessions_create(
        participants={"fp:agent:planner", "fp:tool:weather"},
        roles={"fp:agent:planner": {"coordinator"}, "fp:tool:weather": {"provider"}},
    )

    activity = server.activities_start(
        session_id=session.session_id,
        owner_entity_id="fp:tool:weather",
        initiator_entity_id="fp:agent:planner",
        operation="weather.lookup",
        input_payload={"city": "Paris"},
    )

    print(activity.state.value)
    print(server.activities_result(activity_id=activity.activity_id))


if __name__ == "__main__":
    main()
