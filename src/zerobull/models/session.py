"""Session response models."""

from typing import Any

from ._base import ZeroBullModel

__all__ = ["ControllerSession", "SessionPhone"]


class SessionPhone(ZeroBullModel):
    """A phone available to a phone-controller session."""

    id: str
    name: str
    video_live: bool
    input_present: bool
    can_control: bool
    model: str | None
    os_version: str | None

    @property
    def slot(self) -> str:
        """The phone's slot id."""
        return self.id


class ControllerSession(ZeroBullModel):
    """Phones, socket URL and ICE servers for a WebSocket connection."""

    phones: list[SessionPhone]
    socket_url: str
    ice_servers: list[dict[str, Any]]
    farm_online: bool
