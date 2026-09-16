"""Session resources."""

from .._operations import session
from .._resource import AsyncResource, SyncResource
from ..models.session import ControllerSession


class Session(SyncResource):
    """Synchronous phone-controller session resource."""

    def create(self) -> ControllerSession:
        """Create a phone-controller session.

        Returns the phones you can use and a short-lived ``socket_url``.
        Most users should use ``client.socket()`` instead of calling this
        directly.
        """
        return self._execute(session.create())


class AsyncSession(AsyncResource):
    """Asynchronous phone-controller session resource."""

    async def create(self) -> ControllerSession:
        """Create a phone-controller session.

        Returns the phones you can use and a short-lived ``socket_url``.
        Most users should use ``client.socket()`` instead of calling this
        directly.
        """
        return await self._execute(session.create())
