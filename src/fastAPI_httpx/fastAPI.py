import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, TypedDict

import httpx2
from fastapi import FastAPI, Query, Request, Response
from fastapi.logger import logger

from fastAPI_httpx.http_client import UPSTREAM_URL, HTTPClient, fetch_json
from fastAPI_httpx.services import Report


class State(TypedDict):
    http_client: httpx2.AsyncClient


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[State]:
    """Open one shared AsyncClient at startup and close it at shutdown."""
    timeout = httpx2.Timeout(timeout=2)
    limits = httpx2.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx2.AsyncClient(timeout=timeout, limits=limits, http2=True) as client:
        logger.info("HTTP client opened")
        yield {"http_client": client}
    logger.info("HTTP client closed")


app = FastAPI(docs_url="/", lifespan=lifespan)


@app.get("/endpoint")
async def endpoint(client: HTTPClient) -> dict[str, Any]:
    return await fetch_json(client, UPSTREAM_URL)


@app.get("/endpoint_multi")
async def endpoint_multi(client: HTTPClient) -> dict[str, int]:
    # both upstream calls run concurrently
    first, second = await asyncio.gather(fetch_json(client, UPSTREAM_URL), fetch_json(client, UPSTREAM_URL))
    return {"success": first["success"] + second["success"]}


@app.get("/endpoint_complex_codebase")
async def endpoint_complex_codebase(report: Report, calls: Annotated[int, Query(ge=1, le=10)] = 3) -> dict[str, int]:
    # the endpoint asks for a service, not for the HTTP client (see services.py)
    return await report.build_report(calls)


@app.post("/endpoint_stream")
async def endpoint_stream(request: Request) -> Response:
    body = bytearray(b"RST")
    async for chunk in request.stream():
        body += chunk
    return Response(bytes(body), media_type="text/plain")


if __name__ == "__main__":  # local dev
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
