![Python](https://github.com/raphaelauv/fastAPI-httpx-example/workflows/Python/badge.svg?branch=main)

# Full example of [FastAPI](https://github.com/tiangolo/fastapi) with a [httpx2](https://github.com/pydantic/httpx2) client

### This is an example with FastAPI, but you can use this logic with any async ( ASGI ) web framework


### [EXAMPLE FOR AIOHTTP](https://github.com/raphaelauv/fastAPI-aiohttp-example/)


#### Implemented logic : 

(with a fake server mocking answer of httpx2, through `httpx2.MockTransport`)

- Open AsyncClient at fastAPI startup

- Close AsyncClient at fastAPI shutdown

(both through a FastAPI `lifespan`)


## Tests
- fastAPI endpoint test
- httpx2 test
