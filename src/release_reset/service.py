from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request

from .infrai_client import InfraiClient, InfraiError
from .reset_workflow import ResetCommand, ResetDiagnostic, coordinate_reset


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    app.state.infrai = InfraiClient(api_key)
    yield
    await app.state.infrai.close()


app = FastAPI(title="Release reset bridge", lifespan=lifespan)


@app.post("/developer-resets", response_model=ResetDiagnostic)
async def create_developer_reset(
    command: ResetCommand, request: Request
) -> ResetDiagnostic:
    try:
        return await coordinate_reset(command, request.app.state.infrai)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
