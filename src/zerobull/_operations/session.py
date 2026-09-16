"""Session operations."""

from ..models.session import ControllerSession
from ._base import Operation, RestRequest, parse_model_unwrapped


def create() -> Operation[ControllerSession]:
    """Create a phone-controller session (REST-only)."""
    return Operation(
        rest=RestRequest("GET", "/v1/phone-controller"),
        fun=None,
        parse_rest=parse_model_unwrapped(ControllerSession),
    )
