"""Runs resources."""

from .._resource import AsyncResource, SyncResource


class Runs(SyncResource):
    """Synchronous runs resource."""


class AsyncRuns(AsyncResource):
    """Asynchronous runs resource."""
