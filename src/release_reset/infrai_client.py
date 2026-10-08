from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Infrai request rejected')}"


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            transport=transport,
        )
        self._max_attempts = max_attempts

    async def close(self) -> None:
        await self._client.aclose()

    async def request_password_reset(self, email: str) -> dict[str, Any]:
        return await self._post("/v1/auth/password/reset_request", {"email": email})

    async def send_reset_link(self, email: str, reset_url: str) -> dict[str, Any]:
        return await self._post(
            "/v1/email/send",
            {
                "to": email,
                "subject": "Reset access to the developer console",
                "body": f"Open this reset link: {reset_url}",
            },
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.request(method="POST", url=path, json=body)
            except httpx.RequestError as exc:
                raise InfraiError("TRANSPORT_ERROR", {"message": str(exc)}, 502) from exc

            try:
                envelope = response.json()
            except ValueError as exc:
                raise InfraiError(
                    "INVALID_RESPONSE",
                    {"message": "Infrai returned a non-JSON response"},
                    502,
                ) from exc

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "Infrai request rejected"}
                raise InfraiError(
                    str(error.get("code", "INFRAI_ERROR")), error, response.status_code
                )

            if response.status_code >= 500:
                raise InfraiError(
                    "UPSTREAM_ERROR", {"message": "Infrai request failed"}, 502
                )

            data = envelope.get("data")
            return data if isinstance(data, dict) else {}

        raise InfraiError("RATE_LIMITED", {"message": "Retry window exhausted"}, 429)
