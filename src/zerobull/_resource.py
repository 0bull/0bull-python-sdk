"""Thin shared resource plumbing."""

from typing import TypeVar

from ._operations._base import Operation
from ._transport._base import AsyncTransport, SyncTransport
from ._transport.http import AsyncHTTPTransport, SyncHTTPTransport

T = TypeVar("T")


class SyncResource:
    """Base resource with operation and signed-upload transports."""

    def __init__(self, transport: SyncTransport, http: SyncHTTPTransport) -> None:
        self._transport = transport
        self._http = http

    def _execute(self, op: Operation[T]) -> T:
        return self._transport.execute(op)


class AsyncResource:
    """Async resource with operation and signed-upload transports."""

    def __init__(self, transport: AsyncTransport, http: AsyncHTTPTransport) -> None:
        self._transport = transport
        self._http = http

    async def _execute(self, op: Operation[T]) -> T:
        return await self._transport.execute(op)
