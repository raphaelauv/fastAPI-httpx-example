"""The shared httpx2 client: how endpoints and services get it, and a small helper to call upstream."""

from typing import Annotated, Any

import httpx2
from fastapi import Depends, HTTPException, Request

UPSTREAM_URL = "http://localhost:8080/test"


def get_http_client(request: Request) -> httpx2.AsyncClient:
    """Return the client opened by the app lifespan (override this in tests)."""
    client: httpx2.AsyncClient = request.state.http_client
    return client


HTTPClient = Annotated[httpx2.AsyncClient, Depends(get_http_client)]


async def fetch_json(client: httpx2.AsyncClient, url: str) -> dict[str, Any]:
    """POST to an upstream URL and return its JSON body, mapping upstream failures to a 502."""
    try:
        response = await client.post(url)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
    except (httpx2.HTTPError, ValueError) as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}") from e
    return result
