"""Session operations."""

from ..models.session import ControllerSession
from ._base import Operation, RestRequest, RestResponse


def _parse(response: RestResponse) -> ControllerSession:
    return ControllerSession.model_validate(response.json())


def create() -> Operation[ControllerSession]:
    """Create a phone-controller session (REST-only)."""
    return Operation(rest=RestRequest("GET", "/v1/phone-controller"), fun=None, parse_rest=_parse)
