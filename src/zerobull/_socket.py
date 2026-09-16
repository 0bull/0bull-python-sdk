"""Public synchronous and asynchronous WebSocket clients."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from types import TracebackType

from ._errors import SocketClosedError
from ._operations._base import Operation, SocketFun
from ._transport.http import AsyncHTTPTransport, SyncHTTPTransport
from ._transport.socket import AsyncSocketTransport, SyncSocketTransport
from .models.events import Event
from .models.session import ControllerSession
from .resources.accounts import Accounts, AsyncAccounts
from .resources.billing import AsyncBilling, Billing
from .resources.phones import AsyncPhones, Phones
from .resources.runs import AsyncRuns, Runs
from .resources.submissions import AsyncSubmissions, Submissions
from .resources.uploads import AsyncUploads, Uploads


def _call(fun: str, data: Mapping[str, object] | None) -> Operation[object]:
    return Operation(None, SocketFun(fun, data), lambda response: None, lambda data: data)


class Socket:
    """Socket resources and events; connect explicitly or enter a context manager."""

    def __init__(
        self,
        http: SyncHTTPTransport,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
    ) -> None:
        self._transport = SyncSocketTransport(
            http,
            call_timeout=call_timeout,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            ping_interval=ping_interval,
        )
        self.accounts = Accounts(self._transport, http)
        self.uploads = Uploads(self._transport, http)
        self.submissions = Submissions(self._transport, http)
        self.phones = Phones(self._transport, http)
        self.runs = Runs(self._transport, http)
        self.billing = Billing(self._transport, http)

    @property
    def session(self) -> ControllerSession:
        """The session from the latest successful connection.

        Raises:
            SocketClosedError: If no connection has been established yet.
        """
        session = self._transport.session
        if session is None:
            raise SocketClosedError("Socket has not connected")
        return session

    def connect(self) -> None:
        """Fetch a session and establish the socket connection."""
        self._transport.connect()

    def close(self) -> None:
        """Close the socket and stop reconnecting."""
        self._transport.close()

    def events(self, timeout: float | None = None) -> Iterator[Event]:
        """Yield typed pushes, stopping after timeout seconds without an event.

        User closure ends iteration cleanly; exhausted reconnects raise SocketClosedError.
        """
        return self._transport.events(timeout)

    def call(self, fun: str, data: Mapping[str, object] | None = None) -> object:
        """Call an unmodeled fun and return raw data with standard API error mapping."""
        return self._transport.execute(_call(fun, data))

    def __enter__(self) -> Socket:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncSocket:
    """Socket resources and events; connect explicitly or enter a context manager."""

    def __init__(
        self,
        http: AsyncHTTPTransport,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
    ) -> None:
        self._transport = AsyncSocketTransport(
            http,
            call_timeout=call_timeout,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            ping_interval=ping_interval,
        )
        self.accounts = AsyncAccounts(self._transport, http)
        self.uploads = AsyncUploads(self._transport, http)
        self.submissions = AsyncSubmissions(self._transport, http)
        self.phones = AsyncPhones(self._transport, http)
        self.runs = AsyncRuns(self._transport, http)
        self.billing = AsyncBilling(self._transport, http)

    @property
    def session(self) -> ControllerSession:
        """The session from the latest successful connection.

        Raises:
            SocketClosedError: If no connection has been established yet.
        """
        session = self._transport.session
        if session is None:
            raise SocketClosedError("Socket has not connected")
        return session

    async def connect(self) -> None:
        """Fetch a session and establish the socket connection."""
        await self._transport.connect()

    async def aclose(self) -> None:
        """Close the socket and stop reconnecting."""
        await self._transport.aclose()

    def events(self, timeout: float | None = None) -> AsyncIterator[Event]:
        """Yield typed pushes, stopping after timeout seconds without an event.

        User closure ends iteration cleanly; exhausted reconnects raise SocketClosedError.
        """
        return self._transport.events(timeout)

    async def call(self, fun: str, data: Mapping[str, object] | None = None) -> object:
        """Call an unmodeled fun and return raw data with standard API error mapping."""
        return await self._transport.execute(_call(fun, data))

    async def __aenter__(self) -> AsyncSocket:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
