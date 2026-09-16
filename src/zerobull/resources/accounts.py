"""Accounts resources."""

from .._resource import AsyncResource, SyncResource


class Accounts(SyncResource):
    """Synchronous accounts resource."""


class AsyncAccounts(AsyncResource):
    """Asynchronous accounts resource."""
