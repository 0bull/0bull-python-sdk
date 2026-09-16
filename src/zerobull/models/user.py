"""Authenticated user response."""

from datetime import datetime

from ._base import ZeroBullModel

__all__ = ["User"]


class User(ZeroBullModel):
    """The authenticated API user."""

    id: int
    name: str
    email: str
    email_verified_at: datetime | None
