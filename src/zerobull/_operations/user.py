"""Authenticated user operation (REST only)."""

from ..models.user import User
from ._base import Operation, RestRequest, parse_model


def get() -> Operation[User]:
    """Get the authenticated user."""
    return Operation(RestRequest("GET", "/user"), None, parse_model(User))
