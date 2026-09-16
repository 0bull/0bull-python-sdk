"""Phone responses and documented input types."""

from collections.abc import Mapping
from typing import Literal

from ._base import ZeroBullModel

__all__ = ["CommandOp", "Hotkey", "MacroParams", "Phone"]

Hotkey = Literal["home", "app_switcher", "control_center", "notifications", "paste", "run_shortcut"]
CommandOp = Literal[
    "clipboard_set",
    "clipboard_get",
    "open_url",
    "reboot",
    "clear_photos",
    "get_ip",
    "brightness",
    "wifi",
    "airplane",
    "cellular",
    "flashlight",
]
MacroParams = Mapping[str, str | int | float | bool]


class Phone(ZeroBullModel):
    """A visible phone and its current control availability."""

    slot: str
    name: str
    video_live: bool
    input_present: bool
    can_control: bool
    model: str | None
    os_version: str | None
