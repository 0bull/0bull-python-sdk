"""Synchronous and asynchronous REST clients."""

from __future__ import annotations

from types import TracebackType

import httpx

from ._config import ClientOptions
from ._socket import AsyncSocket, Socket
from ._transport.http import AsyncHTTPTransport, SyncHTTPTransport
from .resources.accounts import Accounts, AsyncAccounts
from .resources.billing import AsyncBilling, Billing
from .resources.phones import AsyncPhones, Phones
from .resources.runs import AsyncRuns, Runs
from .resources.session import AsyncSession, Session
from .resources.submissions import AsyncSubmissions, Submissions
from .resources.uploads import AsyncUploads, Uploads
from .resources.user import AsyncUserResource, UserResource


class ZeroBull:
    """0bull REST client with grouped API resources."""

    def __init__(
        self,
        api_token: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._options = ClientOptions(api_token, base_url, timeout, max_retries)
        self._http = SyncHTTPTransport(self._options, http_client)
        self.user = UserResource(self._http, self._http)
        self.accounts = Accounts(self._http, self._http)
        self.uploads = Uploads(self._http, self._http)
        self.submissions = Submissions(self._http, self._http)
        self.phones = Phones(self._http, self._http)
        self.runs = Runs(self._http, self._http)
        self.billing = Billing(self._http, self._http)
        self.session = Session(self._http, self._http)

    def socket(
        self,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
    ) -> Socket:
        """Create an unconnected socket; enter it or call connect() to start."""
        return Socket(
            self._http,
            call_timeout=call_timeout,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            ping_interval=ping_interval,
        )

    def close(self) -> None:
        """Release connections owned by this client."""
        self._http.close()

    def __enter__(self) -> ZeroBull:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncZeroBull:
    """0bull REST client with grouped API resources."""

    def __init__(
        self,
        api_token: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._options = ClientOptions(api_token, base_url, timeout, max_retries)
        self._http = AsyncHTTPTransport(self._options, http_client)
        self.user = AsyncUserResource(self._http, self._http)
        self.accounts = AsyncAccounts(self._http, self._http)
        self.uploads = AsyncUploads(self._http, self._http)
        self.submissions = AsyncSubmissions(self._http, self._http)
        self.phones = AsyncPhones(self._http, self._http)
        self.runs = AsyncRuns(self._http, self._http)
        self.billing = AsyncBilling(self._http, self._http)
        self.session = AsyncSession(self._http, self._http)

    def socket(
        self,
        *,
        call_timeout: float = 60,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        ping_interval: float | None = 20,
    ) -> AsyncSocket:
        """Create an unconnected socket; enter it or call connect() to start."""
        return AsyncSocket(
            self._http,
            call_timeout=call_timeout,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            ping_interval=ping_interval,
        )

    async def aclose(self) -> None:
        """Release connections owned by this client."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncZeroBull:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
