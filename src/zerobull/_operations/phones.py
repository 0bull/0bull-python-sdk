"""Phone operations shared by REST and socket resources."""

from __future__ import annotations

import base64
import builtins
from collections.abc import Mapping, Sequence
from typing import get_args

from pydantic import TypeAdapter

from ..models.phones import CommandOp, Hotkey, MacroParams, Phone
from ..models.runs import Run
from ._base import (
    Operation,
    RestRequest,
    SocketFun,
    compact,
    no_content,
    parse_model,
    parse_model_socket,
    path_segment,
    require_range,
    unwrap,
)


def list() -> Operation[builtins.list[Phone]]:
    """List visible phones."""
    parse = TypeAdapter(builtins.list[Phone]).validate_python
    return Operation(
        RestRequest("GET", "/v1/phones"),
        SocketFun("/app/phones/list", {}),
        lambda response: parse(unwrap(response)),
        parse,
    )


def snapshot(slot: str, *, width: int | None = None) -> Operation[bytes]:
    """Capture a JPEG, optionally resized to width (120-2000)."""
    require_range("width", width, 120, 2000)
    return Operation(
        RestRequest(
            "GET", f"/v1/phones/{path_segment(slot)}/snapshot", params=compact({"width": width})
        ),
        SocketFun("/app/phones/snapshot", compact({"slot": slot, "width": width})),
        lambda response: response.content,
        lambda data: base64.b64decode(
            TypeAdapter(dict[str, str]).validate_python(data)["image"], validate=True
        ),
    )


def _text(data: object) -> str:
    return TypeAdapter(dict[str, str]).validate_python(data)["text"]


def ocr(slot: str, *, width: int | None = None) -> Operation[str]:
    """Read on-screen text, optionally resizing to width (120-2000)."""
    require_range("width", width, 120, 2000)
    return Operation(
        RestRequest(
            "GET", f"/v1/phones/{path_segment(slot)}/ocr", params=compact({"width": width})
        ),
        SocketFun("/app/phones/ocr", compact({"slot": slot, "width": width})),
        lambda response: _text(response.json()),
        _text,
    )


def _input(slot: str, body: Mapping[str, object]) -> Operation[None]:
    body = compact(body)
    return Operation(
        RestRequest("POST", f"/v1/phones/{path_segment(slot)}/input", json=body),
        SocketFun("/app/phones/input", {"slot": slot, **body}),
        no_content,
        no_content,
    )


def tap(slot: str, *, fx: float, fy: float) -> Operation[None]:
    """Tap at fractional screen coordinates (0-1)."""
    require_range("fx", fx, 0, 1)
    require_range("fy", fy, 0, 1)
    return _input(slot, {"op": "tap", "fx": fx, "fy": fy})


def swipe(
    slot: str, *, fx1: float, fy1: float, fx2: float, fy2: float, steps: int | None = None
) -> Operation[None]:
    """Swipe between fractional coordinates, using 1-500 steps if supplied."""
    for name, value in (("fx1", fx1), ("fy1", fy1), ("fx2", fx2), ("fy2", fy2)):
        require_range(name, value, 0, 1)
    require_range("steps", steps, 1, 500)
    return _input(
        slot, {"op": "swipe", "fx1": fx1, "fy1": fy1, "fx2": fx2, "fy2": fy2, "steps": steps}
    )


def hotkey(slot: str, key: Hotkey) -> Operation[None]:
    """Send a documented phone hotkey."""
    if key not in get_args(Hotkey):
        raise ValueError("Unknown hotkey")
    return _input(slot, {"op": "hotkey", "key": key})


def type(slot: str, text: str) -> Operation[None]:
    """Type text on the phone."""
    return _input(slot, {"op": "type", "text": text})


def _run(slot: str, suffix: str, body: Mapping[str, object]) -> Operation[Run]:
    body = compact(body)
    return Operation(
        RestRequest("POST", f"/v1/phones/{path_segment(slot)}/{suffix}", json=body),
        SocketFun(f"/app/phones/{suffix}", {"slot": slot, **body}),
        parse_model(Run),
        parse_model_socket(Run),
    )


def run_command(
    slot: str,
    op: CommandOp,
    *,
    text: str | None = None,
    url: str | None = None,
    level: float | None = None,
    on: bool | None = None,
) -> Operation[Run]:
    """Queue a command with its required text, URL, level, or on value."""
    if op not in get_args(CommandOp):
        raise ValueError("Unknown command op")
    body = {"op": op, "text": text, "url": url, "level": level, "on": on}
    required = {
        "clipboard_set": "text",
        "open_url": "url",
        "brightness": "level",
        "wifi": "on",
        "airplane": "on",
        "cellular": "on",
        "flashlight": "on",
    }.get(op)
    if required is not None and body[required] is None:
        raise ValueError(f"{op} requires {required}")
    require_range("level", level, 0, 1)
    return _run(slot, "commands", body)


def run_macro(
    slot: str,
    *,
    workflow: str | None = None,
    params: MacroParams | None = None,
    steps: Sequence[Mapping[str, object]] | None = None,
) -> Operation[Run]:
    """Queue exactly one workflow (with scalar params) or up to 200 steps."""
    if (workflow is None) == (steps is None):
        raise ValueError("Provide exactly one of workflow or steps")
    if params is not None:
        if workflow is None:
            raise ValueError("params requires workflow")
        if any(not isinstance(value, (str, int, float, bool)) for value in params.values()):
            raise ValueError("params values must be str, int, float, or bool")
    if steps is not None:
        if len(steps) > 200:
            raise ValueError("steps must contain at most 200 entries")
        if any(
            not isinstance(step, Mapping) or not isinstance(step.get("action"), str)
            for step in steps
        ):
            raise ValueError("Each step requires a string action")
    return _run(
        slot,
        "macros",
        {
            "workflow": workflow,
            "params": dict(params) if params is not None else None,
            "steps": [dict(step) for step in steps] if steps is not None else None,
        },
    )


def run_agent(slot: str, task: str) -> Operation[Run]:
    """Queue a non-empty agent task of at most 2000 characters."""
    if not task or len(task) > 2000:
        raise ValueError("task must contain 1-2000 characters")
    return _run(slot, "agent-runs", {"task": task})
