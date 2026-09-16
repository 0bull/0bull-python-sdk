"""Billing resources."""

from .._resource import AsyncResource, SyncResource


class Billing(SyncResource):
    """Synchronous billing resource."""


class AsyncBilling(AsyncResource):
    """Asynchronous billing resource."""
