from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


class BuildEvent(str, Enum):
    FAILED = "failed"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"


class ReleaseOperation(str, Enum):
    PROMOTE = "promote"
    ROLLBACK = "rollback"
    RETRY = "retry"


class ResetCommand(BaseModel):
    developer_email: str
    reset_url: HttpUrl
    build_id: str
    build_event: BuildEvent
    release_operation: ReleaseOperation

    @field_validator("developer_email")
    @classmethod
    def validate_developer_email(cls, value: str) -> str:
        local, separator, domain = value.strip().partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("developer_email must be a valid email address")
        return value.strip()


class ResetDiagnostic(BaseModel):
    build_id: str
    build_event: BuildEvent
    release_operation: ReleaseOperation
    reset_registered: bool
    notification_queued: bool
    message_id: str | None = None


async def coordinate_reset(
    command: ResetCommand, provider: Any
) -> ResetDiagnostic:
    email = str(command.developer_email)
    await provider.request_password_reset(email)
    delivery = await provider.send_reset_link(email, str(command.reset_url))
    message_id = delivery.get("message_id")
    return ResetDiagnostic(
        build_id=command.build_id,
        build_event=command.build_event,
        release_operation=command.release_operation,
        reset_registered=True,
        notification_queued=True,
        message_id=str(message_id) if message_id is not None else None,
    )
