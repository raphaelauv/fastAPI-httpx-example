from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from fastAPI_httpx.fastAPI import app, Singletonhttpx


class HTTPXMock:
    """Minimal replacement for pytest_httpx (which only supports httpx, not httpx2).

    Queues responses per (method, url) and serves them through an httpx2.MockTransport.
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], list[httpx2.Response]] = {}

    def add_response(self, method: str, url: str, status_code: int = 200, json: object = None) -> None:
        self._responses.setdefault((method, url), []).append(httpx2.Response(status_code, json=json))

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        queue = self._responses.get((request.method, str(request.url)))
        assert queue, f"No response registered for {request.method} {request.url}"
        return queue.pop(0)

    def assert_all_responses_used(self) -> None:
        unused = {key: len(queue) for key, queue in self._responses.items() if queue}
        assert not unused, f"Registered responses were not requested: {unused}"


@pytest.fixture
def httpx_mock() -> Iterator[HTTPXMock]:
    mock = HTTPXMock()
    Singletonhttpx.httpx_client = httpx2.AsyncClient(transport=httpx2.MockTransport(mock.handler))
    yield mock
    Singletonhttpx.httpx_client = None
    mock.assert_all_responses_used()


@pytest.fixture
def client_fastAPI() -> TestClient:
    return TestClient(app=app)


@pytest.mark.asyncio
async def test_query_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="http://test/toto", json={"result": 2})
    rst = await Singletonhttpx.query_url("http://test/toto")
    assert rst == {"result": 2}


@pytest.mark.asyncio
async def test_query_url_error_status(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="http://test/toto", status_code=500, json="boom")
    rst = await Singletonhttpx.query_url("http://test/toto")
    assert rst == {"ERROR OCCURED": '"boom"'}


def test_endpoint(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", json={"success": 1})

    result: httpx2.Response = client_fastAPI.get(url='/endpoint')
    assert result.json() == {'success': 1}


def test_endpoint_multi(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", json={"success": 1})
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", json={"success": 2})

    result: httpx2.Response = client_fastAPI.get(url='/endpoint_multi')
    assert result.json() == {'success': 3}


def test_endpoint_stream(client_fastAPI: TestClient) -> None:
    data = b'TOTO' * 10000

    with client_fastAPI.stream('POST', url='/endpoint_stream/', content=data) as result:
        result.read()
        assert result.content == b'RST' + data


def test_lifespan_opens_and_closes_client() -> None:
    with TestClient(app=app):
        assert Singletonhttpx.httpx_client is not None
    assert Singletonhttpx.httpx_client is None
