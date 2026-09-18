"""Session response models."""

from ._base import ZeroBullModel

__all__ = ["ControllerSession", "SessionPhone"]


class SessionPhone(ZeroBullModel):
    """A phone available to a phone-controller session."""

    slot: str
    name: str
    video_live: bool
    input_present: bool
    can_control: bool
    model: str | None
    os_version: str | None


class ControllerSession(ZeroBullModel):
    """Phones and a socket URL for a WebSocket connection."""

    phones: list[SessionPhone]
    socket_url: str
    farm_online: bool
