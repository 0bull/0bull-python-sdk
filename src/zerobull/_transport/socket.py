"""WebSocket request multiplexing, push events, and bounded reconnects."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import queue
import threading
import time
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import suppress
from typing import TypedDict, TypeVar

from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection as AsyncConnection
from websockets.asyncio.client import connect as async_connect
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.sync.client import ClientConnection as SyncConnection
from websockets.sync.client import connect as sync_connect

from .._errors import (
    APIConnectionError,
    APITimeoutError,
    SocketClosedError,
    ZeroBullError,
    error_from_status,
)
from .._operations import session
from .._operations._base import Operation, compact
from ..models.events import BillingRequestEvent, Event, RunEvent, SubmissionEvent
from ..models.session import ControllerSession
from .http import AsyncHTTPTransport, SyncHTTPTransport


class _PingOptions(TypedDict, total=False):
    ping_interval: float | None


T = TypeVar("T")
_SYNC_KEEPALIVE = "ping_interval" in inspect.signature(sync_connect).parameters
# Handshake debug logging would disclose the credential in the request URL.
_logger = logging.Logger(__name__)
_logger.disabled = True


def _frame(message: str | bytes) -> dict[str, object]:
    if not isinstance(message, str):
        return {}
    try:
        value = json.loads(message)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _event(frame: dict[str, object]) -> Event | None:
    name = frame.get("event")
    try:
        if name == "run":
            return RunEvent.model_validate({"run": frame.get("data")})
        if name == "submission":
            return SubmissionEvent.model_validate({"submission": frame.get("data")})
        if name == "billing_request":
            return BillingRequestEvent.model_validate({"request": frame.get("data")})
    except ValidationError:
        pass
    return None


def _check_operation(op: Operation[T]) -> None:
    if op.fun is None or op.parse_socket is None:
        name = op.rest.path if op.rest else "Operation"
        raise NotImplementedError(f"{name} is not available over WebSocket")


def _parse(op: Operation[T], reply: dict[str, object]) -> T:
    status = reply.get("status")
    if not isinstance(status, int):
        raise APIConnectionError("Invalid socket reply status")
    if not 200 <= status < 300:
        raise error_from_status(
            status, {"message": reply.get("message"), "errors": reply.get("errors")}
        )
    assert op.parse_socket is not None
    return op.parse_socket(reply.get("data"))


class SyncSocketTransport:
    """Execute socket operations with a dedicated daemon reader thread."""

    supports_rest = False

    def __init__(
        self,
        http: SyncHTTPTransport,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
        reconnect_delay: float = 0.5,
    ) -> None:
        self._http = http
        self.call_timeout = call_timeout
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        self._reconnect_delay = reconnect_delay
        self.session: ControllerSession | None = None
        self._condition = threading.Condition()
        self._connect_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._ws: SyncConnection | None = None
        self._reader: threading.Thread | None = None
        self._pending: dict[str, Future[dict[str, object]]] = {}
        self._events: queue.Queue[Event | SocketClosedError | None] = queue.Queue()
        self._counter = 0
        self._ended = False

    def _open(self) -> None:
        current = self._http.execute(session.create())
        ping_options: _PingOptions = (
            {"ping_interval": self.ping_interval} if _SYNC_KEEPALIVE else {}
        )
        try:
            ws = sync_connect(
                current.socket_url,
                **ping_options,
                max_size=16 * 1024 * 1024,
                open_timeout=self.call_timeout,
                logger=_logger,
            )
        except TimeoutError:
            raise APITimeoutError("Socket connection timed out") from None
        except (OSError, WebSocketException):
            raise APIConnectionError("Socket connection failed") from None
        with self._condition:
            if not self._stop.is_set():
                self.session = current
                self._ws = ws
                self._condition.notify_all()
                return
        ws.close()
        raise SocketClosedError("Socket is closed")

    def connect(self) -> None:
        """Fetch a session and connect; repeated calls while connected are harmless."""
        with self._connect_lock:
            if self._stop.is_set() or self._ended:
                raise SocketClosedError("Socket is closed")
            if self._reader is not None:
                return
            self._open()
            self._reader = threading.Thread(target=self._read, daemon=True)
            self._reader.start()

    def _disconnect(self) -> None:
        with self._condition:
            self._ws = None
            for future in self._pending.values():
                future.set_exception(SocketClosedError("Socket connection closed"))
            self._pending.clear()
            self._condition.notify_all()

    def _finish(self) -> None:
        with self._condition:
            self._ended = True
            self._condition.notify_all()
        self._events.put(
            None if self._stop.is_set() else SocketClosedError("Socket connection closed")
        )

    def _messages(self, ws: SyncConnection) -> Iterator[str | bytes]:
        if _SYNC_KEEPALIVE or self.ping_interval is None:
            yield from ws
            return
        # websockets 13-14 expose protocol pings but no threading keepalive.
        next_ping = time.monotonic() + self.ping_interval
        while not self._stop.is_set():
            if time.monotonic() >= next_ping:
                if not ws.ping().wait(timeout=20):
                    ws.close()
                    return
                next_ping = time.monotonic() + self.ping_interval
            with suppress(TimeoutError):
                yield ws.recv(timeout=max(0, next_ping - time.monotonic()))

    def _read(self) -> None:
        while not self._stop.is_set():
            ws = self._ws
            if ws is None:
                break
            try:
                for message in self._messages(ws):
                    frame = _frame(message)
                    msgid = frame.get("msgid")
                    with self._condition:
                        future = self._pending.pop(msgid, None) if isinstance(msgid, str) else None
                        if future is not None:
                            future.set_result(frame)
                    if future is None:
                        event = _event(frame)
                        if event is not None:
                            self._events.put(event)
            except (ConnectionClosed, OSError):
                pass
            self._disconnect()
            if self._stop.is_set() or not self.auto_reconnect:
                break
            for attempt in range(self.max_reconnect_attempts):
                if self._stop.wait(min(self._reconnect_delay * 2**attempt, 10)):
                    break
                try:
                    self._open()
                    break
                except (ZeroBullError, ValueError):
                    continue
            if self._ws is None:
                break
        self._finish()

    def execute(self, operation: Operation[T]) -> T:
        """Send once, match the reply by msgid, and enforce a call deadline."""
        _check_operation(operation)
        assert operation.fun is not None
        deadline = time.monotonic() + self.call_timeout
        future: Future[dict[str, object]] = Future()
        with self._condition:
            while self._ws is None:
                if self._reader is None or self._ended or self._stop.is_set():
                    raise SocketClosedError("Socket is not connected")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise APITimeoutError("Socket call timed out")
                self._condition.wait(remaining)
            ws = self._ws
            self._counter += 1
            msgid = str(self._counter)
            self._pending[msgid] = future
        try:
            frame = json.dumps(
                {"fun": operation.fun.fun, "msgid": msgid, "data": compact(operation.fun.data)}
            )
            if not self._send_lock.acquire(timeout=max(0, deadline - time.monotonic())):
                raise APITimeoutError("Socket call timed out")
            try:
                ws.send(frame)
            finally:
                self._send_lock.release()
            reply = future.result(timeout=max(0, deadline - time.monotonic()))
        except FutureTimeout:
            raise APITimeoutError("Socket call timed out") from None
        except (ConnectionClosed, OSError):
            raise SocketClosedError("Socket connection closed") from None
        finally:
            with self._condition:
                self._pending.pop(msgid, None)
        return _parse(operation, reply)

    def events(self, timeout: float | None = None) -> Iterator[Event]:
        """Yield pushes until closed or idle for timeout seconds."""
        while True:
            try:
                event = self._events.get(timeout=timeout)
            except queue.Empty:
                return
            if event is None or isinstance(event, SocketClosedError):
                self._events.put(event)
                if event is not None and not self._stop.is_set():
                    raise event
                return
            yield event

    def close(self) -> None:
        """Stop reconnecting, fail pending calls, and end event iteration."""
        self._stop.set()
        ws = self._ws
        self._disconnect()
        self._finish()
        if ws is not None:
            ws.close()
        if self._reader is not None:
            self._reader.join(timeout=self.call_timeout)


class AsyncSocketTransport:
    """Execute socket operations with a dedicated asyncio reader task."""

    supports_rest = False

    def __init__(
        self,
        http: AsyncHTTPTransport,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
        reconnect_delay: float = 0.5,
    ) -> None:
        self._http = http
        self.call_timeout = call_timeout
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        self._reconnect_delay = reconnect_delay
        self.session: ControllerSession | None = None
        self._connect_lock = asyncio.Lock()
        self._ready = asyncio.Event()
        self._ws: AsyncConnection | None = None
        self._reader: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[dict[str, object]]] = {}
        self._events: asyncio.Queue[Event | SocketClosedError | None] = asyncio.Queue()
        self._counter = 0
        self._closed = False
        self._ended = False

    async def _open(self) -> None:
        current = await self._http.execute(session.create())
        try:
            ws = await async_connect(
                current.socket_url,
                ping_interval=self.ping_interval,
                max_size=16 * 1024 * 1024,
                open_timeout=self.call_timeout,
                logger=_logger,
            )
        except asyncio.TimeoutError:
            raise APITimeoutError("Socket connection timed out") from None
        except (OSError, WebSocketException):
            raise APIConnectionError("Socket connection failed") from None
        if self._closed:
            await ws.close()
            raise SocketClosedError("Socket is closed")
        self.session = current
        self._ws = ws
        self._ready.set()

    async def connect(self) -> None:
        """Fetch a session and connect; repeated calls while connected are harmless."""
        async with self._connect_lock:
            if self._closed or self._ended:
                raise SocketClosedError("Socket is closed")
            if self._reader is not None:
                return
            await self._open()
            self._reader = asyncio.create_task(self._read())

    def _disconnect(self) -> None:
        self._ws = None
        self._ready.clear()
        for future in self._pending.values():
            if not future.done():
                future.set_exception(SocketClosedError("Socket connection closed"))
        self._pending.clear()

    def _finish(self) -> None:
        self._ended = True
        self._ready.set()
        self._events.put_nowait(
            None if self._closed else SocketClosedError("Socket connection closed")
        )

    async def _read(self) -> None:
        try:
            while not self._closed:
                ws = self._ws
                if ws is None:
                    break
                try:
                    async for message in ws:
                        frame = _frame(message)
                        msgid = frame.get("msgid")
                        future = self._pending.pop(msgid, None) if isinstance(msgid, str) else None
                        if future is not None:
                            if not future.done():
                                future.set_result(frame)
                        else:
                            event = _event(frame)
                            if event is not None:
                                self._events.put_nowait(event)
                except (ConnectionClosed, OSError):
                    pass
                self._disconnect()
                if self._closed or not self.auto_reconnect:
                    break
                for attempt in range(self.max_reconnect_attempts):
                    await asyncio.sleep(min(self._reconnect_delay * 2**attempt, 10))
                    try:
                        await self._open()
                        break
                    except (ZeroBullError, ValueError):
                        continue
                if self._ws is None:
                    break
        finally:
            self._finish()

    async def _execute(self, operation: Operation[T]) -> T:
        assert operation.fun is not None
        if self._reader is None:
            raise SocketClosedError("Socket is not connected")
        await self._ready.wait()
        ws = self._ws
        if ws is None or self._closed:
            raise SocketClosedError("Socket is not connected")
        self._counter += 1
        msgid = str(self._counter)
        frame = json.dumps(
            {"fun": operation.fun.fun, "msgid": msgid, "data": compact(operation.fun.data)}
        )
        future: asyncio.Future[dict[str, object]] = asyncio.get_running_loop().create_future()
        self._pending[msgid] = future
        try:
            await ws.send(frame)
            reply = await future
        except (ConnectionClosed, OSError):
            raise SocketClosedError("Socket connection closed") from None
        finally:
            self._pending.pop(msgid, None)
            if not future.cancelled() and future.done():
                future.exception()
        return _parse(operation, reply)

    async def execute(self, operation: Operation[T]) -> T:
        """Send once and bound both reconnection waiting and reply waiting."""
        _check_operation(operation)
        try:
            return await asyncio.wait_for(self._execute(operation), self.call_timeout)
        except asyncio.TimeoutError:
            raise APITimeoutError("Socket call timed out") from None

    async def events(self, timeout: float | None = None) -> AsyncIterator[Event]:
        """Yield pushes until closed or idle for timeout seconds."""
        while True:
            try:
                event = await asyncio.wait_for(self._events.get(), timeout)
            except asyncio.TimeoutError:
                return
            if event is None or isinstance(event, SocketClosedError):
                self._events.put_nowait(event)
                if event is not None and not self._closed:
                    raise event
                return
            yield event

    async def aclose(self) -> None:
        """Stop reconnecting, fail pending calls, and end event iteration."""
        self._closed = True
        ws = self._ws
        self._disconnect()
        self._finish()
        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
        if ws is not None:
            await ws.close()
