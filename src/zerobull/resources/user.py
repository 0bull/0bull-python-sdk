"""Authenticated user resources."""

from .._operations import user
from .._resource import AsyncResource, SyncResource
from ..models.user import User


class UserResource(SyncResource):
    """Synchronous authenticated user access."""

    def get(self) -> User:
        """Get the authenticated user."""
        return self._execute(user.get())


class AsyncUserResource(AsyncResource):
    """Asynchronous authenticated user access."""

    async def get(self) -> User:
        """Get the authenticated user."""
        return await self._execute(user.get())
