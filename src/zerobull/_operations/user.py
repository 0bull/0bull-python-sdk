"""Authenticated user operation (REST only)."""

from ..models.user import User
from ._base import Operation, RestRequest, parse_model


def get() -> Operation[User]:
    """Get the authenticated user."""
    return Operation(rest=RestRequest("GET", "/user"), fun=None, parse_rest=parse_model(User))
