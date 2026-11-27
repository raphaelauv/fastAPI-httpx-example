![Python](https://github.com/raphaelauv/fastAPI-httpx2-example/workflows/Python/badge.svg?branch=main)

# Full example of [FastAPI](https://github.com/tiangolo/fastapi) with a [httpx2](https://github.com/pydantic/httpx2) client

### This is an example with FastAPI, but you can use this logic with any async ( ASGI ) web framework

### [EXAMPLE FOR AIOHTTP](https://github.com/raphaelauv/fastAPI-aiohttp-example/)

#### Implemented logic :

- Open one shared `AsyncClient` at FastAPI startup and close it at shutdown, in a FastAPI `lifespan`
- Hand the client to endpoints through the lifespan state and `Depends`
- Turn upstream failures (connection errors, non-2xx answers) into a `502`
- Run several upstream calls concurrently with `asyncio.gather`
- Use the client deep in a codebase without passing it through every function (`/endpoint_complex_codebase`)

#### Code layout

- [`fastAPI.py`](src/fastAPI_httpx/fastAPI.py): the app, its `lifespan` and the endpoints
- [`http_client.py`](src/fastAPI_httpx/http_client.py): the `HTTPClient` dependency and the `fetch_json` helper
- [`services.py`](src/fastAPI_httpx/services.py): service classes used by `/endpoint_complex_codebase`

#### Using the client deep in your code

`/endpoint` and `/endpoint_multi` receive the client with `Depends` and pass it as an argument.
That's fine for one level, but in a real codebase the HTTP call is often several functions deep.

`/endpoint_complex_codebase` shows how to avoid passing the client through every call:
each class receives what it needs **once, in its constructor**, and FastAPI builds the chain for every request.

```text
endpoint_complex_codebase(report: Report)       # only asks for the service
  -> ReportService(upstream: UpstreamAPI)       # business logic, never sees the client
       -> UpstreamAPI(client: HTTPClient)       # the only class that talks HTTP
            -> httpx2.AsyncClient               # opened and closed by the lifespan
```

Inside the classes, methods use `self.upstream` / `self.client`, so no call takes the client as an argument.
Tests still swap the client in one place: overriding `get_http_client` reaches it deep inside `UpstreamAPI`.

| Where the client lives | You write | Cost |
|---|---|---|
| Function arguments | `f(client, ...)` at every level | Verbose once the calls get deep |
| An object (this repo's services) | One `Depends` per endpoint, `self.client` inside | Needs a class |
| A module global set by the lifespan | `get_client()` anywhere | Hidden dependency; tests must patch the global |

## Run

```bash
uv sync --all-extras
uv run python src/fastAPI_httpx/fastAPI.py
```

## Tests

The tests swap the real client for a mocked one with `app.dependency_overrides`,
so no real upstream server is needed.

```bash
uv run pytest
```

### Why a custom `HTTPXMock` fixture?

The tests mock outgoing httpx2 calls with a small `HTTPXMock` fixture built on
[`httpx2.MockTransport`](https://github.com/pydantic/httpx2/blob/main/docs/advanced/transports.md),
because there is no official httpx2 equivalent of `pytest_httpx`'s `HTTPXMock` yet:

- [pytest_httpx](https://github.com/Colin-b/pytest_httpx) only supports `httpx` (it pins `httpx==0.28.*`).
- [pytest-httpx2](https://github.com/lundberg/pytest-httpx2) exists, but it builds on respx, which still
  depends on `httpx` and is typed around `httpx.Response`.

Once [respx ships httpx2 support](https://github.com/lundberg/respx/issues/316), the fixture can be
replaced by it.
