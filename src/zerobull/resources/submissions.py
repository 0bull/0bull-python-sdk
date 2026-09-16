"""Submissions resources."""

from .._resource import AsyncResource, SyncResource


class Submissions(SyncResource):
    """Synchronous submissions resource."""


class AsyncSubmissions(AsyncResource):
    """Asynchronous submissions resource."""
