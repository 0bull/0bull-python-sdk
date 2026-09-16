"""Phones resources."""

from .._resource import AsyncResource, SyncResource


class Phones(SyncResource):
    """Synchronous phones resource."""


class AsyncPhones(AsyncResource):
    """Asynchronous phones resource."""
