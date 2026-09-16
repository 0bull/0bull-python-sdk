"""Session resources."""

from .._resource import AsyncResource, SyncResource


class Session(SyncResource):
    """Synchronous session resource."""


class AsyncSession(AsyncResource):
    """Asynchronous session resource."""
