"""Uploads resources."""

from .._resource import AsyncResource, SyncResource


class Uploads(SyncResource):
    """Synchronous uploads resource."""


class AsyncUploads(AsyncResource):
    """Asynchronous uploads resource."""
