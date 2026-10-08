import asyncio
from typing import Any

from release_reset.reset_workflow import ResetCommand, coordinate_reset


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    async def request_password_reset(self, email: str) -> dict[str, Any]:
        self.calls.append(("reset_request", email, None))
        return {}

    async def send_reset_link(
        self, email: str, reset_url: str
    ) -> dict[str, Any]:
        self.calls.append(("email_send", email, reset_url))
        return {"message_id": "msg_release_42"}


def test_release_reset_is_observable_after_both_operations() -> None:
    provider = RecordingProvider()
    command = ResetCommand(
        developer_email="maintainer@example.com",
        reset_url="https://console.example.com/reset?t=opaque-token",
        build_id="build-1842",
        build_event="blocked",
        release_operation="rollback",
    )

    result = asyncio.run(coordinate_reset(command, provider))

    assert provider.calls == [
        ("reset_request", "maintainer@example.com", None),
        (
            "email_send",
            "maintainer@example.com",
            "https://console.example.com/reset?t=opaque-token",
        ),
    ]
    assert result.model_dump() == {
        "build_id": "build-1842",
        "build_event": "blocked",
        "release_operation": "rollback",
        "reset_registered": True,
        "notification_queued": True,
        "message_id": "msg_release_42",
    }
