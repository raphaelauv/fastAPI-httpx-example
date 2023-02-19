import json

import httpx
from fastapi.testclient import TestClient
import pytest
from pytest_httpx import HTTPXMock
from fastAPI_httpx.fastAPI import app, Singletonhttpx


@pytest.fixture
def client_fastAPI():
    return TestClient(app=app)


@pytest.fixture
def non_mocked_hosts() -> list:
    return ["testserver"]  # disable mock of starlette test client


@pytest.mark.asyncio
async def test_query_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url="http://test/toto", status_code=200,
                            content=json.dumps({"result": 2}).encode('utf-8'))
    rst = await Singletonhttpx.query_url("http://test/toto")
    assert rst == {"result": 2}


def test_endpoint(httpx_mock: HTTPXMock, client_fastAPI):
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", status_code=200,
                            content=json.dumps({"success": 1}).encode('utf-8'))

    result: httpx.Response = client_fastAPI.get(url='/endpoint/')
    assert result is not None

    result_json = result.json()
    assert result_json == {'success': 1}


def test_endpoint_multi(httpx_mock: HTTPXMock, client_fastAPI):
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", status_code=200,
                            content=json.dumps({"success": 1}).encode('utf-8'))
    httpx_mock.add_response(method="POST", url="http://localhost:8080/test", status_code=200,
                            content=json.dumps({"success": 2}).encode('utf-8'))

    result: httpx.Response = client_fastAPI.get(url='/endpoint_multi/')
    assert result is not None

    result_json = result.json()
    assert result_json == {'success': 3}


def test_endpoint_stream(client_fastAPI):
    data = b'TOTO' * 10000

    with client_fastAPI.stream('POST', url='/endpoint_stream/', content=data) as result:
        assert result is not None
        result.read()
        rst = result.content
        assert rst == b'RST' + data
