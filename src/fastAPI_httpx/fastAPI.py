import asyncio
from collections.abc import Coroutine

from typing import List, Optional, Any, Dict

import httpx
from fastapi import FastAPI
from fastapi.logger import logger as fastAPI_logger  # convenient name
from fastapi.requests import Request
from fastapi.responses import Response

SIZE_POOL_httpx = 100


class Singletonhttpx:
    httpx_client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_httpx_client(cls) -> httpx.AsyncClient:
        if cls.httpx_client is None:
            timeout = httpx.Timeout(timeout=2)
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            cls.httpx_client = httpx.AsyncClient(timeout=timeout, limits=limits, http2=True)

        return cls.httpx_client

    @classmethod
    async def close_httpx_client(cls) -> None:
        if cls.httpx_client:
            await cls.httpx_client.close()
            cls.httpx_client = None

    @classmethod
    async def query_url(cls, url: str) -> Any:
        client = cls.get_httpx_client()

        try:
            response = await client.post(url)
            if response.status_code != 200:
                return {"ERROR OCCURED" + str(await response.text())}

            json_result = response.json()
        except Exception as e:
            return {"ERROR": e}

        return json_result


async def on_start_up() -> None:
    fastAPI_logger.info("on_start_up")
    Singletonhttpx.get_httpx_client()


async def on_shutdown() -> None:
    fastAPI_logger.info("on_shutdown")
    await Singletonhttpx.close_httpx_client()


app = FastAPI(docs_url="/", on_startup=[on_start_up], on_shutdown=[on_shutdown])


@app.get('/endpoint')
async def endpoint() -> Any:
    url = "http://localhost:8080/test"

    return await Singletonhttpx.query_url(url)


@app.get('/endpoint_multi')
async def endpoint_multi() -> Dict[str, int]:
    url = "http://localhost:8080/test"

    async_calls: List[Coroutine[Any, Any, Any]] = list()  # store all async operations

    async_calls.append(Singletonhttpx.query_url(url))
    async_calls.append(Singletonhttpx.query_url(url))

    all_results: List[Dict[Any, Any]] = await asyncio.gather(*async_calls)  # wait for all async operations
    return {'success': sum([x['success'] for x in all_results])}


@app.post("/endpoint_stream/")
async def endpoint_stream(request: Request):
    body = b'RST'
    async for chunk in request.stream():
        body += chunk

    return Response(body, media_type='text/plain')


if __name__ == '__main__':  # local dev
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
