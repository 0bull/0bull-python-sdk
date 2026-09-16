import json

import httpx
import pytest

from tests.conftest import MockAPI
from zerobull._config import ClientOptions
from zerobull._errors import APIConnectionError, APITimeoutError, BadRequestError, RateLimitError
from zerobull._operations._base import Operation, RestRequest, SocketFun, no_content
from zerobull._transport.http import AsyncHTTPTransport, SyncHTTPTransport

OP = Operation(
    RestRequest("POST", "/thing", params={"yes": 1, "no": None}, json={"yes": False, "no": None}),
    None,
    no_content,
)


def test_headers_body(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/thing", status=204)
    assert mock_api.client._http.execute(OP) is None
    request = mock_api.requests[-1]
    assert request.headers["authorization"] == "Bearer test"
    assert request.headers["accept"] == "application/json"
    assert request.headers["user-agent"] == "0bull-python/0.1.0"
    assert dict(request.url.params) == {"yes": "1"}
    assert json.loads(request.content) == {"yes": False}


def test_multipart_upload(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/video", status=204)
    op = Operation(
        RestRequest(
            "POST",
            "/video",
            data={"draft": True, "other": False, "omit": None},
            files={"video": ("a.mp4", b"video", "video/mp4")},
        ),
        None,
        no_content,
    )
    mock_api.client._http.execute(op)
    body = mock_api.requests[-1].content
    assert b'name="draft"\r\n\r\n1' in body and b'name="other"\r\n\r\n0' in body
    assert b"omit" not in body and b"video/mp4" in body
    mock_api.add("POST", "/signed", json={"ok": True})
    assert mock_api.client._http.upload("https://upload.example/signed", b"video") == {"ok": True}
    assert "authorization" not in mock_api.requests[-1].headers


@pytest.mark.parametrize(
    "header,delay", [("0.25", 0.25), ("bad", 1), (None, 1), ("100", 60), ("-1", 1), ("nan", 1)]
)
def test_retries(header: str | None, delay: float, no_sleep: list[float]) -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(
            429,
            json={"message": "slow"},
            headers={"Retry-After": header} if header is not None else {},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        transport = SyncHTTPTransport(ClientOptions("test"), client)
        with pytest.raises(RateLimitError) as caught:
            transport.execute(OP)
        assert count == 3 and no_sleep == [delay, delay]
        assert caught.value.retry_after == delay


@pytest.mark.parametrize(
    "exception,expected",
    [(httpx.ReadTimeout, APITimeoutError), (httpx.ConnectError, APIConnectionError)],
)
def test_network(exception: type[httpx.TransportError], expected: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception("broken")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(expected) as caught:
            SyncHTTPTransport(ClientOptions("test"), client).execute(OP)
        assert isinstance(caught.value.__cause__, exception)


def test_no_rest(mock_api: MockAPI) -> None:
    with pytest.raises(NotImplementedError, match="/app/test is not available over HTTP"):
        mock_api.client._http.execute(Operation(None, SocketFun("/app/test"), no_content))


def test_text_error(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/thing", status=400, content=b"bad")
    with pytest.raises(BadRequestError, match="bad"):
        mock_api.client._http.execute(OP)


@pytest.mark.anyio
async def test_async_transport(mock_api: MockAPI, no_sleep: list[float]) -> None:
    mock_api.add("POST", "/api/thing", status=204)
    await mock_api.async_client._http.execute(OP)
    mock_api.add("POST", "/signed", status=204)
    assert (
        await mock_api.async_client._http.upload("https://upload.example/signed", b"video") is None
    )
    assert "authorization" not in mock_api.requests[-1].headers
    mock_api.add("POST", "/api/thing", status=429, headers={"Retry-After": "0"})
    with pytest.raises(RateLimitError):
        await mock_api.async_client._http.execute(OP)
    assert no_sleep == [0, 0]
    with pytest.raises(NotImplementedError):
        await mock_api.async_client._http.execute(
            Operation(None, SocketFun("/app/test"), no_content)
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exception,expected",
    [(httpx.ReadTimeout, APITimeoutError), (httpx.ConnectError, APIConnectionError)],
)
async def test_async_network(
    exception: type[httpx.TransportError], expected: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception("broken")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(expected):
            await AsyncHTTPTransport(ClientOptions("test"), client).execute(OP)


@pytest.mark.anyio
async def test_injected_auth_not_sent_to_upload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    with httpx.Client(
        transport=transport, auth=("user", "password"), headers={"Authorization": "Bearer injected"}
    ) as client:
        http = SyncHTTPTransport(ClientOptions("test"), client)
        assert http.upload("https://upload.example/signed", b"video") == {"ok": True}
    async with httpx.AsyncClient(
        transport=transport, auth=("user", "password"), headers={"Authorization": "Bearer injected"}
    ) as client_async:
        http_async = AsyncHTTPTransport(ClientOptions("test"), client_async)
        assert await http_async.upload("https://upload.example/signed", b"video") == {"ok": True}
    assert all("authorization" not in request.headers for request in requests)


@pytest.mark.anyio
async def test_retry_success_replays_files(no_sleep: list[float]) -> None:
    import io

    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(429 if len(bodies) % 2 else 204)

    op = Operation(
        RestRequest("POST", "/video", files={"video": io.BytesIO(b"clip")}), None, no_content
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        SyncHTTPTransport(ClientOptions("test"), client).execute(op)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client_async:
        await AsyncHTTPTransport(ClientOptions("test"), client_async).execute(op)
    assert bodies[0] == bodies[1] and bodies[2] == bodies[3]
    assert all(b"clip" in body for body in bodies)
    assert no_sleep == [1, 1]


@pytest.mark.anyio
async def test_file_free_multipart(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/video", status=204)
    op = Operation(
        RestRequest(
            "POST",
            "/video",
            data={"draft": False, "video_url": "https://example.com/video"},
            params={"draft": False},
        ),
        None,
        no_content,
    )
    await mock_api.async_client._http.execute(op)
    record = mock_api.records[-1]
    assert record["data"] == {"draft": "0", "video_url": "https://example.com/video"}
    assert record["query"] == {"draft": "false"}
    assert record["files"] == {}


def test_empty_error_and_no_mapping(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/thing", status=400, content=b"")
    with pytest.raises(BadRequestError, match="HTTP 400"):
        mock_api.client._http.execute(OP)
    with pytest.raises(NotImplementedError, match="Operation"):
        mock_api.client._http.execute(Operation(None, None, no_content))
