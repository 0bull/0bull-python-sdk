"""Scriptable local WebSocket server for both execution modes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from threading import Thread
from types import TracebackType
from typing import Any

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

Handler = Callable[[ServerConnection, dict[str, Any]], Awaitable[None]]


class SocketServer:
    def __init__(self, handler: Handler | None = None) -> None:
        self.handler = handler
        self.replies: dict[str, dict[str, object]] = {}
        self.frames: list[dict[str, Any]] = []
        self.connections: list[ServerConnection] = []
        self.server: Server | None = None
        self.url = ""

    async def _handle(self, ws: ServerConnection) -> None:
        self.connections.append(ws)
        tasks: list[asyncio.Task[None]] = []
        try:
            async for message in ws:
                frame = json.loads(message)
                self.frames.append(frame)
                tasks.append(asyncio.create_task(self._reply(ws, frame)))
        except ConnectionClosed:
            pass
        finally:
            for task in tasks:
                task.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    raise result

    async def _reply(self, ws: ServerConnection, frame: dict[str, Any]) -> None:
        if self.handler:
            await self.handler(ws, frame)
        else:
            reply = self.replies.get(frame["fun"], {"status": 200, "data": frame["data"]})
            await ws.send(json.dumps({"msgid": frame["msgid"], **reply}))

    async def __aenter__(self) -> SocketServer:
        self.server = await serve(self._handle, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{next(iter(self.server.sockets)).getsockname()[1]}"
        return self

    async def __aexit__(self, *args: object) -> None:
        assert self.server is not None
        self.server.close()
        await self.server.wait_closed()

    def __enter__(self) -> SocketServer:
        ready: Future[None] = Future()

        async def run() -> None:
            self.loop = asyncio.get_running_loop()
            self.stop = asyncio.Event()
            async with self:
                ready.set_result(None)
                await self.stop.wait()

        self.thread = Thread(target=lambda: asyncio.run(run()), daemon=True)
        self.thread.start()
        ready.result(timeout=5)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.loop.call_soon_threadsafe(self.stop.set)
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()


def session_body(url: str) -> dict[str, object]:
    return {"phones": [], "socket_url": url, "farm_online": True}
