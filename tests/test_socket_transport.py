"""Socket transport behavior against real local connections."""

import asyncio
import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from pydantic import ValidationError as ModelValidationError
from websockets.asyncio.server import ServerConnection

from zerobull import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    BillingRequestEvent,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RunEvent,
    SocketClosedError,
    SubmissionEvent,
    UnavailableError,
    ValidationError,
)
from zerobull._operations import session
from zerobull._operations._base import Operation, SocketFun
from zerobull._transport.socket import AsyncSocketTransport, SyncSocketTransport

from .conftest import MockAPI
from .socket_server import SocketServer, session_body
from .test_billing import REQUEST_STATUS
from .test_phones import RUN
from .test_submissions import SUBMISSION


def echo() -> Operation[object]:
    return Operation(
        None, SocketFun("/echo", {"keep": 1, "omit": None}), lambda r: None, lambda d: d
    )


def test_sync_execute(mock_api: MockAPI) -> None:
    with SocketServer() as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        transport = SyncSocketTransport(mock_api.client._http)
        transport.connect()
        try:
            assert transport.execute(echo()) == {"keep": 1}
            assert isinstance(server.frames[0]["msgid"], str)
            with pytest.raises(NotImplementedError, match="not available over WebSocket"):
                transport.execute(session.create())
        finally:
            transport.close()


@pytest.mark.anyio
async def test_async_execute(mock_api: MockAPI) -> None:
    async with SocketServer() as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        transport = AsyncSocketTransport(mock_api.async_client._http)
        await transport.connect()
        try:
            assert await transport.execute(echo()) == {"keep": 1}
            assert isinstance(server.frames[0]["msgid"], str)
            with pytest.raises(NotImplementedError, match="not available over WebSocket"):
                await transport.execute(session.create())
        finally:
            await transport.aclose()


ERRORS = [
    (400, BadRequestError),
    (403, PermissionDeniedError),
    (404, NotFoundError),
    (409, ConflictError),
    (422, ValidationError),
    (500, InternalServerError),
    (502, UnavailableError),
    (503, UnavailableError),
    (418, APIStatusError),
]


@pytest.mark.parametrize("status,error", ERRORS)
def test_sync_errors(mock_api: MockAPI, status: int, error: type[APIStatusError]) -> None:
    with SocketServer() as server:
        server.replies["/echo"] = {
            "status": status,
            "message": "rejected",
            "errors": {"slot": ["bad"]},
        }
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket() as socket:
            with pytest.raises(error) as caught:
                socket.call("/echo")
            assert caught.value.status == status
            assert caught.value.message == "rejected"
            assert caught.value.errors == {"slot": ["bad"]}


@pytest.mark.anyio
@pytest.mark.parametrize("status,error", ERRORS)
async def test_async_errors(mock_api: MockAPI, status: int, error: type[APIStatusError]) -> None:
    async with SocketServer() as server:
        server.replies["/echo"] = {
            "status": status,
            "message": "rejected",
            "errors": {"slot": ["bad"]},
        }
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket() as socket:
            with pytest.raises(error) as caught:
                await socket.call("/echo")
            assert caught.value.status == status
            assert caught.value.message == "rejected"
            assert caught.value.errors == {"slot": ["bad"]}


async def reverse_replies(ws: ServerConnection, frame: dict[str, Any]) -> None:
    if frame["data"]["index"] == 0:
        return
    await ws.send(json.dumps({"msgid": frame["msgid"], "status": 200, "data": 1}))
    await ws.send(json.dumps({"msgid": str(int(frame["msgid"]) - 1), "status": 200, "data": 0}))


def test_sync_out_of_order(mock_api: MockAPI) -> None:
    with SocketServer(reverse_replies) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(call_timeout=2) as socket, ThreadPoolExecutor() as pool:
            # The server acknowledges receipt independently of the reply.
            received = threading.Event()
            original = server.handler

            async def handler(ws: ServerConnection, frame: dict[str, Any]) -> None:
                received.set()
                assert original is not None
                await original(ws, frame)

            server.handler = handler
            first = pool.submit(socket.call, "/echo", {"index": 0})
            assert received.wait(2)
            second = pool.submit(socket.call, "/echo", {"index": 1})
            assert second.result(2) == 1
            assert first.result(2) == 0
            assert len({frame["msgid"] for frame in server.frames}) == 2


@pytest.mark.anyio
async def test_async_out_of_order(mock_api: MockAPI) -> None:
    received = asyncio.Event()

    async def handler(ws: ServerConnection, frame: dict[str, Any]) -> None:
        received.set()
        await reverse_replies(ws, frame)

    async with SocketServer(handler) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket(call_timeout=2) as socket:
            first = asyncio.create_task(socket.call("/echo", {"index": 0}))
            await asyncio.wait_for(received.wait(), 2)
            second = asyncio.create_task(socket.call("/echo", {"index": 1}))
            assert list(await asyncio.gather(first, second)) == [0, 1]
            assert len({frame["msgid"] for frame in server.frames}) == 2


async def no_reply(ws: ServerConnection, frame: dict[str, Any]) -> None:
    await asyncio.Event().wait()


def test_sync_timeout(mock_api: MockAPI) -> None:
    with SocketServer(no_reply) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(call_timeout=0.05) as socket:
            with pytest.raises(APITimeoutError):
                socket.call("/echo")
            assert not socket._transport._pending


@pytest.mark.anyio
async def test_async_timeout_and_cancel(mock_api: MockAPI) -> None:
    received = asyncio.Event()

    async def handler(ws: ServerConnection, frame: dict[str, Any]) -> None:
        received.set()

    async with SocketServer(handler) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket(call_timeout=0.05) as socket:
            with pytest.raises(APITimeoutError):
                await socket.call("/echo")
            assert not socket._transport._pending
            received.clear()
            call = asyncio.create_task(socket.call("/echo"))
            await received.wait()
            call.cancel()
            with pytest.raises(asyncio.CancelledError):
                await call
            assert not socket._transport._pending


async def push_frames(ws: ServerConnection, frame: dict[str, Any]) -> None:
    for junk in (
        b"binary",
        "invalid json",
        "[]",
        "null",
        '{"event":"unknown"}',
        '{"msgid":[]}',
        '{"event":"run","data":{}}',
        '{"msgid":"unmatched","status":200}',
        "{}",
    ):
        await ws.send(junk)
    for name, data in (
        ("run", RUN),
        ("submission", SUBMISSION),
        ("billing_request", REQUEST_STATUS),
    ):
        await ws.send(json.dumps({"event": name, "data": {**data, "future_field": True}}))
    await ws.send(json.dumps({"msgid": frame["msgid"], "status": 204, "data": None}))


def check_events(events: list[object]) -> None:
    assert len(events) == 3
    run, submission, billing = events
    assert isinstance(run, RunEvent) and run.run.id == RUN["id"]
    assert isinstance(submission, SubmissionEvent) and submission.submission.id == SUBMISSION["id"]
    assert (
        isinstance(billing, BillingRequestEvent)
        and billing.request.request_id == REQUEST_STATUS["request_id"]
    )
    with pytest.raises(ModelValidationError):
        run.__setattr__("run", run.run)


def test_sync_events_and_junk(mock_api: MockAPI) -> None:
    with SocketServer(push_frames) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket() as socket:
            assert socket.call("/push") is None
            check_events(list(socket.events(timeout=0.01)))


@pytest.mark.anyio
async def test_async_events_and_junk(mock_api: MockAPI) -> None:
    async with SocketServer(push_frames) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket() as socket:
            assert await socket.call("/push") is None
            check_events([event async for event in socket.events(timeout=0.01)])


def test_sync_reconnect(mock_api: MockAPI) -> None:
    with SocketServer() as replacement:

        async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
            mock_api.add("GET", "/api/v1/phone-controller", json=session_body(replacement.url))
            await ws.close(code=1011)

        with SocketServer(drop) as original:
            mock_api.add("GET", "/api/v1/phone-controller", json=session_body(original.url))
            with mock_api.client.socket(call_timeout=2) as socket:
                socket._transport._reconnect_delay = 0.001
                with pytest.raises(SocketClosedError):
                    socket.call("/drop")
                assert socket.call("/echo", {"ok": True}) == {"ok": True}
                assert socket.session.socket_url == replacement.url
                assert len(mock_api.requests) == 2
                assert len(original.frames) == len(replacement.frames) == 1


@pytest.mark.anyio
async def test_async_reconnect(mock_api: MockAPI) -> None:
    async with SocketServer() as replacement:

        async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
            mock_api.add("GET", "/api/v1/phone-controller", json=session_body(replacement.url))
            await ws.close(code=1011)

        async with SocketServer(drop) as original:
            mock_api.add("GET", "/api/v1/phone-controller", json=session_body(original.url))
            async with mock_api.async_client.socket(call_timeout=2) as socket:
                socket._transport._reconnect_delay = 0.001
                with pytest.raises(SocketClosedError):
                    await socket.call("/drop")
                assert await socket.call("/echo", {"ok": True}) == {"ok": True}
                assert socket.session.socket_url == replacement.url
                assert len(mock_api.requests) == 2
                assert len(original.frames) == len(replacement.frames) == 1


@pytest.mark.parametrize("attempts", [0, 2])
def test_sync_reconnect_exhausted(mock_api: MockAPI, attempts: int) -> None:
    async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
        mock_api.add("GET", "/api/v1/phone-controller", status=503)
        await ws.close()

    with SocketServer(drop) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(max_reconnect_attempts=attempts, call_timeout=1) as socket:
            socket._transport._reconnect_delay = 0.001
            with pytest.raises(SocketClosedError):
                socket.call("/drop")
            with pytest.raises(SocketClosedError):
                list(socket.events(timeout=2))
            assert len(mock_api.requests) == attempts + 1
            with pytest.raises(SocketClosedError):
                socket.call("/future")
            with pytest.raises(SocketClosedError):
                socket.connect()


@pytest.mark.anyio
@pytest.mark.parametrize("attempts", [0, 2])
async def test_async_reconnect_exhausted(mock_api: MockAPI, attempts: int) -> None:
    async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
        mock_api.add("GET", "/api/v1/phone-controller", status=503)
        await ws.close()

    async with SocketServer(drop) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket(
            max_reconnect_attempts=attempts, call_timeout=1
        ) as socket:
            socket._transport._reconnect_delay = 0.001
            with pytest.raises(SocketClosedError):
                await socket.call("/drop")
            with pytest.raises(SocketClosedError):
                _ = [event async for event in socket.events(timeout=2)]
            assert len(mock_api.requests) == attempts + 1
            with pytest.raises(SocketClosedError):
                await socket.call("/future")
            with pytest.raises(SocketClosedError):
                await socket.connect()


def test_sync_manual_close_pending(mock_api: MockAPI) -> None:
    received = threading.Event()

    async def handler(ws: ServerConnection, frame: dict[str, Any]) -> None:
        received.set()

    with SocketServer(handler) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket() as socket, ThreadPoolExecutor() as pool:
            socket.connect()
            call = pool.submit(socket.call, "/pending")
            events = pool.submit(lambda: list(socket.events()))
            assert received.wait(2)
            socket.close()
            with pytest.raises(SocketClosedError):
                call.result(2)
            assert events.result(2) == []
            assert len(mock_api.requests) == 1
        assert list(socket.events()) == []


@pytest.mark.anyio
async def test_async_manual_close_pending(mock_api: MockAPI) -> None:
    received = asyncio.Event()

    async def handler(ws: ServerConnection, frame: dict[str, Any]) -> None:
        received.set()

    async with SocketServer(handler) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket() as socket:
            await socket.connect()
            call = asyncio.create_task(socket.call("/pending"))

            async def consume() -> list[object]:
                return [event async for event in socket.events()]

            events = asyncio.create_task(consume())
            await asyncio.wait_for(received.wait(), 2)
            await socket.aclose()
            with pytest.raises(SocketClosedError):
                await call
            assert await events == []
            assert len(mock_api.requests) == 1
        assert [event async for event in socket.events()] == []


def test_sync_unconnected(mock_api: MockAPI) -> None:
    socket = mock_api.client.socket()
    with pytest.raises(SocketClosedError):
        socket.call("/echo")
    with pytest.raises(SocketClosedError):
        _ = socket.session
    socket.close()
    with pytest.raises(SocketClosedError):
        socket.connect()


@pytest.mark.anyio
async def test_async_unconnected(mock_api: MockAPI) -> None:
    socket = mock_api.async_client.socket()
    with pytest.raises(SocketClosedError):
        await socket.call("/echo")
    with pytest.raises(SocketClosedError):
        _ = socket.session
    await socket.aclose()
    with pytest.raises(SocketClosedError):
        await socket.connect()


def test_sync_invalid_reply(mock_api: MockAPI) -> None:
    with SocketServer() as server:
        server.replies["/echo"] = {"data": None}
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with (
            mock_api.client.socket() as socket,
            pytest.raises(APIConnectionError, match="reply status"),
        ):
            socket.call("/echo")


@pytest.mark.anyio
async def test_async_invalid_reply(mock_api: MockAPI) -> None:
    async with SocketServer() as server:
        server.replies["/echo"] = {"data": None}
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket() as socket:
            with pytest.raises(APIConnectionError, match="reply status"):
                await socket.call("/echo")


@pytest.mark.parametrize("auto_reconnect", [False, True])
def test_sync_close_during_reconnect(mock_api: MockAPI, auto_reconnect: bool) -> None:
    async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
        await ws.close()

    with SocketServer(drop) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(auto_reconnect=auto_reconnect, call_timeout=0.05) as socket:
            socket._transport._reconnect_delay = 10
            with pytest.raises(SocketClosedError):
                socket.call("/drop")
            with pytest.raises(APITimeoutError if auto_reconnect else SocketClosedError):
                socket.call("/during-reconnect")
            socket.close()
            assert list(socket.events()) == []
            assert len(mock_api.requests) == 1
            assert socket._transport._reader is not None
            assert not socket._transport._reader.is_alive()


@pytest.mark.anyio
@pytest.mark.parametrize("auto_reconnect", [False, True])
async def test_async_close_during_reconnect(mock_api: MockAPI, auto_reconnect: bool) -> None:
    async def drop(ws: ServerConnection, frame: dict[str, Any]) -> None:
        await ws.close()

    async with SocketServer(drop) as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket(
            auto_reconnect=auto_reconnect, call_timeout=0.05
        ) as socket:
            socket._transport._reconnect_delay = 10
            with pytest.raises(SocketClosedError):
                await socket.call("/drop")
            with pytest.raises(APITimeoutError if auto_reconnect else SocketClosedError):
                await socket.call("/during-reconnect")
            await socket.aclose()
            assert [event async for event in socket.events()] == []
            assert len(mock_api.requests) == 1
            assert socket._transport._reader is not None
            assert socket._transport._reader.done()


def test_sync_failed_connect(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phone-controller", json=session_body("invalid://host"))
    socket = mock_api.client.socket()
    with pytest.raises(APIConnectionError, match="Socket connection failed"):
        socket.connect()
    socket.close()


@pytest.mark.anyio
async def test_async_failed_connect(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phone-controller", json=session_body("invalid://host"))
    socket = mock_api.async_client.socket()
    with pytest.raises(APIConnectionError, match="Socket connection failed"):
        await socket.connect()
    await socket.aclose()


def test_sync_snapshot_large(mock_api: MockAPI) -> None:
    jpeg = b"jpeg" * (512 * 1024)
    with SocketServer() as server:
        server.replies["/app/phones/snapshot"] = {
            "status": 200,
            "data": {"image": base64.b64encode(jpeg).decode(), "content_type": "image/jpeg"},
        }
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(ping_interval=None) as socket:
            assert socket.phones.snapshot("phone-1") == jpeg


@pytest.mark.anyio
async def test_async_snapshot_large(mock_api: MockAPI) -> None:
    jpeg = b"jpeg" * (512 * 1024)
    async with SocketServer() as server:
        server.replies["/app/phones/snapshot"] = {
            "status": 200,
            "data": {"image": base64.b64encode(jpeg).decode(), "content_type": "image/jpeg"},
        }
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket(ping_interval=None) as socket:
            assert await socket.phones.snapshot("phone-1") == jpeg


def test_sync_protocol_keepalive_on_older_websockets(
    mock_api: MockAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from zerobull._transport import socket as transport_module

    monkeypatch.setattr(transport_module, "_SYNC_KEEPALIVE", False)
    with SocketServer() as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket(ping_interval=0.01) as socket:
            ws = socket._transport._ws
            assert ws is not None
            pinged = threading.Event()
            original = ws.ping

            def ping(data: Any = None) -> threading.Event:
                result = original(data)
                pinged.set()
                return result

            monkeypatch.setattr(ws, "ping", ping)
            assert pinged.wait(2)
            assert socket.call("/echo", {"after_ping": True}) == {"after_ping": True}
