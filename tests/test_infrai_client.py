import asyncio

import httpx
import pytest

from release_reset.infrai_client import InfraiClient, InfraiError


def test_business_rejection_is_read_from_envelope_before_status() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/auth/password/reset_request"
        return httpx.Response(
            400,
            json={
                "ok": False,
                "data": None,
                "error": {"code": "INVALID_INPUT", "message": "email rejected"},
                "metadata": {},
            },
        )

    async def exercise() -> None:
        client = InfraiClient("test-key", transport=httpx.MockTransport(reject))
        with pytest.raises(InfraiError) as caught:
            await client.request_password_reset("maintainer@example.com")
        await client.close()

        assert caught.value.status_code == 400
        assert caught.value.code == "INVALID_INPUT"

    asyncio.run(exercise())
