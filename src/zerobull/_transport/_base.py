"""Transport protocols shared by resource classes."""

from typing import Protocol, TypeVar

from .._operations._base import Operation

T = TypeVar("T")


class SyncTransport(Protocol):
    """Synchronous operation executor."""

    def execute(self, operation: Operation[T]) -> T: ...


class AsyncTransport(Protocol):
    """Asynchronous operation executor."""

    async def execute(self, operation: Operation[T]) -> T: ...
