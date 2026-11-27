from collections.abc import Iterator

import httpx2
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from fastAPI_httpx.fastAPI import app, lifespan
from fastAPI_httpx.http_client import UPSTREAM_URL, fetch_json, get_http_client


class HTTPXMock:
    """Minimal replacement for pytest_httpx (which only supports httpx, not httpx2).

    Queues responses per (method, url) and serves them through an httpx2.MockTransport.
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], list[httpx2.Response]] = {}
        self.client = httpx2.AsyncClient(transport=httpx2.MockTransport(self._handler))

    def add_response(self, method: str, url: str, status_code: int = 200, json: object = None) -> None:
        self._responses.setdefault((method, url), []).append(httpx2.Response(status_code, json=json))

    def _handler(self, request: httpx2.Request) -> httpx2.Response:
        queue = self._responses.get((request.method, str(request.url)))
        assert queue, f"No response registered for {request.method} {request.url}"
        return queue.pop(0)

    def assert_all_responses_used(self) -> None:
        unused = {key: len(queue) for key, queue in self._responses.items() if queue}
        assert not unused, f"Registered responses were not requested: {unused}"


@pytest.fixture
def httpx_mock() -> Iterator[HTTPXMock]:
    mock = HTTPXMock()
    yield mock
    mock.assert_all_responses_used()


@pytest.fixture
def client_fastAPI(httpx_mock: HTTPXMock) -> Iterator[TestClient]:
    """Test client whose endpoints receive the mocked httpx2 client."""
    app.dependency_overrides[get_http_client] = lambda: httpx_mock.client
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_fetch_json(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="http://test/toto", json={"result": 2})
    assert await fetch_json(httpx_mock.client, "http://test/toto") == {"result": 2}


@pytest.mark.asyncio
async def test_fetch_json_upstream_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="http://test/toto", status_code=500)
    with pytest.raises(HTTPException) as exc_info:
        await fetch_json(httpx_mock.client, "http://test/toto")
    assert exc_info.value.status_code == 502


def test_endpoint(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, json={"success": 1})
    assert client_fastAPI.get("/endpoint").json() == {"success": 1}


def test_endpoint_upstream_error(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, status_code=503)
    assert client_fastAPI.get("/endpoint").status_code == 502


def test_endpoint_multi(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, json={"success": 1})
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, json={"success": 2})
    assert client_fastAPI.get("/endpoint_multi").json() == {"success": 3}


def test_endpoint_complex_codebase(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    # the single get_http_client override reaches the client deep inside ReportService -> UpstreamAPI
    for value in (1, 2, 3):
        httpx_mock.add_response(method="POST", url=UPSTREAM_URL, json={"success": value})
    assert client_fastAPI.get("/endpoint_complex_codebase").json() == {"calls": 3, "success": 6}


def test_endpoint_complex_codebase_calls_param(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, json={"success": 5})
    assert client_fastAPI.get("/endpoint_complex_codebase", params={"calls": 1}).json() == {"calls": 1, "success": 5}


def test_endpoint_complex_codebase_upstream_error(httpx_mock: HTTPXMock, client_fastAPI: TestClient) -> None:
    httpx_mock.add_response(method="POST", url=UPSTREAM_URL, status_code=503)
    assert client_fastAPI.get("/endpoint_complex_codebase", params={"calls": 1}).status_code == 502


def test_endpoint_complex_codebase_calls_bounds(client_fastAPI: TestClient) -> None:
    assert client_fastAPI.get("/endpoint_complex_codebase", params={"calls": 0}).status_code == 422
    assert client_fastAPI.get("/endpoint_complex_codebase", params={"calls": 11}).status_code == 422


def test_endpoint_stream(client_fastAPI: TestClient) -> None:
    data = b"TOTO" * 10000
    response = client_fastAPI.post("/endpoint_stream", content=data)
    assert response.content == b"RST" + data


@pytest.mark.asyncio
async def test_lifespan_opens_and_closes_client() -> None:
    async with lifespan(app) as state:
        client = state["http_client"]
        assert not client.is_closed
    assert client.is_closed
