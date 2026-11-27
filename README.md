![Python](https://github.com/raphaelauv/fastAPI-httpx-example/workflows/Python/badge.svg?branch=main)

# Full example of [FastAPI](https://github.com/tiangolo/fastapi) with a [httpx2](https://github.com/pydantic/httpx2) client

### This is an example with FastAPI, but you can use this logic with any async ( ASGI ) web framework


### [EXAMPLE FOR AIOHTTP](https://github.com/raphaelauv/fastAPI-aiohttp-example/)


#### Implemented logic : 

(with a fake server mocking answer of httpx2, through `httpx2.MockTransport`)

- Open AsyncClient at fastAPI startup

- Close AsyncClient at fastAPI shutdown

(both through a FastAPI `lifespan`)


## Run

```bash
uv sync --all-extras
uv run python src/fastAPI_httpx/fastAPI.py
```

## Tests

```bash
uv run pytest
```

- fastAPI endpoint test
- httpx2 test

### Why a custom `HTTPXMock` fixture?

The tests mock outgoing httpx2 calls with a small `HTTPXMock` fixture built on
[`httpx2.MockTransport`](https://github.com/pydantic/httpx2/blob/main/docs/advanced/transports.md),
because there is no official httpx2 equivalent of `pytest_httpx`'s `HTTPXMock` yet:

- [pytest_httpx](https://github.com/Colin-b/pytest_httpx) only supports `httpx` (it pins `httpx==0.28.*`).
- [pytest-httpx2](https://github.com/lundberg/pytest-httpx2) exists, but it builds on respx, which still
  depends on `httpx` and is typed around `httpx.Response`.

Once [respx ships httpx2 support](https://github.com/lundberg/respx/issues/316), the fixture can be
replaced by it.
