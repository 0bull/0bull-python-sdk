import base64
from typing import Any

import pytest

from tests.conftest import MockAPI
from zerobull._operations import phones

PHONE = {
    "slot": "phone-1",
    "name": "Phone",
    "video_live": True,
    "input_present": False,
    "can_control": True,
    "model": None,
    "os_version": None,
}


def test_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phones", json={"data": [PHONE]})
    result = mock_api.client.phones.list()
    assert result[0].slot == "phone-1"
    assert mock_api.records[-1]["query"] == {}


@pytest.mark.anyio
async def test_async_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phones", json={"data": [PHONE]})
    assert (await mock_api.async_client.phones.list())[0].slot == "phone-1"


RUN = {
    "id": "run-1",
    "slot": "phone-1",
    "kind": "command",
    "status": "queued",
    "label": None,
    "result": None,
    "error": None,
    "started_at": None,
    "finished_at": None,
    "created_at": "2026-09-16T00:00:00Z",
}
JPEG = b"\xff\xd8exact jpeg\xff\xd9"
CASES = [
    ("snapshot", {"width": 120}, "GET", "snapshot", {}, JPEG),
    ("ocr", {"width": 2000}, "GET", "ocr", {}, {"text": "hello"}),
    ("tap", {"fx": 0, "fy": 1}, "POST", "input", {"op": "tap", "fx": 0, "fy": 1}, {"op": "tap"}),
    (
        "swipe",
        {"fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0, "steps": 500},
        "POST",
        "input",
        {"op": "swipe", "fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0, "steps": 500},
        {"op": "swipe"},
    ),
    ("hotkey", {"key": "home"}, "POST", "input", {"op": "hotkey", "key": "home"}, {"op": "hotkey"}),
    ("type", {"text": "hello"}, "POST", "input", {"op": "type", "text": "hello"}, {"op": "type"}),
    (
        "run_command",
        {"op": "wifi", "on": False},
        "POST",
        "commands",
        {"op": "wifi", "on": False},
        {"data": RUN},
    ),
    (
        "run_macro",
        {"workflow": "story", "params": {"caption": "hi", "n": 1, "x": 0.5, "b": False}},
        "POST",
        "macros",
        {"workflow": "story", "params": {"caption": "hi", "n": 1, "x": 0.5, "b": False}},
        {"data": RUN},
    ),
    (
        "run_macro",
        {"steps": [{"action": "tap", "fx": 0.5}]},
        "POST",
        "macros",
        {"steps": [{"action": "tap", "fx": 0.5}]},
        {"data": RUN},
    ),
    (
        "run_agent",
        {"task": "Open Settings"},
        "POST",
        "agent-runs",
        {"task": "Open Settings"},
        {"data": RUN},
    ),
]

CASES += [
    ("run_command", body, "POST", "commands", body, {"data": RUN})
    for body in (
        {"op": "clipboard_set", "text": ""},
        {"op": "clipboard_get"},
        {"op": "open_url", "url": "https://example.com"},
        {"op": "reboot"},
        {"op": "clear_photos"},
        {"op": "get_ip"},
        {"op": "brightness", "level": 0},
        {"op": "brightness", "level": 1},
        {"op": "airplane", "on": True},
        {"op": "cellular", "on": False},
        {"op": "flashlight", "on": True},
    )
]
CASES += [
    ("snapshot", {}, "GET", "snapshot", {}, JPEG),
    ("snapshot", {"width": 2000}, "GET", "snapshot", {}, JPEG),
    ("ocr", {}, "GET", "ocr", {}, {"text": "hello"}),
    ("ocr", {"width": 120}, "GET", "ocr", {}, {"text": "hello"}),
    ("run_macro", {"workflow": "story"}, "POST", "macros", {"workflow": "story"}, {"data": RUN}),
    (
        "run_macro",
        {"steps": [{"action": "tap"}] * 200},
        "POST",
        "macros",
        {"steps": [{"action": "tap"}] * 200},
        {"data": RUN},
    ),
    ("run_agent", {"task": "x" * 2000}, "POST", "agent-runs", {"task": "x" * 2000}, {"data": RUN}),
]
CASES += [
    ("swipe", body, "POST", "input", {"op": "swipe", **body}, {"op": "swipe"})
    for body in (
        {"fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0},
        {"fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0, "steps": 1},
    )
]
CASES += [
    ("hotkey", {"key": key}, "POST", "input", {"op": "hotkey", "key": key}, {"op": "hotkey"})
    for key in ("app_switcher", "control_center", "notifications", "paste", "run_shortcut")
]


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("name,kwargs,method,suffix,body,reply", CASES)
async def test_phone_methods(
    mock_api: MockAPI,
    asynchronous: bool,
    name: str,
    kwargs: dict[str, Any],
    method: str,
    suffix: str,
    body: dict[str, Any],
    reply: Any,
) -> None:
    path = f"/api/v1/phones/phone-1/{suffix}"
    if name == "snapshot":
        mock_api.add(method, path, content=JPEG, headers={"Content-Type": "image/jpeg"})
    else:
        mock_api.add(method, path, json=reply, status=202 if name.startswith("run_") else 200)
    resource = mock_api.async_client.phones if asynchronous else mock_api.client.phones
    result = getattr(resource, name)("phone-1", **kwargs)
    if asynchronous:
        result = await result
    expected = JPEG if name == "snapshot" else "hello" if name == "ocr" else None
    if name.startswith("run_"):
        assert result.id == "run-1" and result.created_at.year == 2026
    else:
        assert result == expected
    record = mock_api.records[-1]
    assert (record["method"], record["path"]) == (method, path)
    assert record["query"] == ({"width": str(kwargs["width"])} if "width" in kwargs else {})
    assert record["json"] == (body if method == "POST" else None)
    operation = getattr(phones, name)("phone-1", **kwargs)
    assert operation.fun.fun == f"/app/phones/{suffix}"
    assert operation.fun.data == {"slot": "phone-1", **(kwargs if method == "GET" else body)}
    socket_reply = (
        {"image": base64.b64encode(JPEG).decode(), "content_type": "image/jpeg"}
        if name == "snapshot"
        else RUN
        if name.startswith("run_")
        else reply
    )
    assert operation.parse_socket(socket_reply) == result


INVALID: list[tuple[str, dict[str, Any]]] = [
    *[(name, {"width": value}) for name in ("snapshot", "ocr") for value in (119, 2001)],
    *[("tap", {"fx": value, "fy": 0.5}) for value in (-0.1, 1.1, float("nan"))],
    ("tap", {"fx": 0.5, "fy": -1}),
    *[
        ("swipe", {**dict.fromkeys(("fx1", "fy1", "fx2", "fy2"), 0.5), key: -1})
        for key in ("fx1", "fy1", "fx2", "fy2")
    ],
    *[("swipe", {"fx1": 0, "fy1": 0, "fx2": 1, "fy2": 1, "steps": value}) for value in (0, 501)],
    ("hotkey", {"key": "unknown"}),
    ("run_command", {"op": "unknown"}),
    *[
        ("run_command", {"op": op})
        for op in (
            "clipboard_set",
            "open_url",
            "brightness",
            "wifi",
            "airplane",
            "cellular",
            "flashlight",
        )
    ],
    *[("run_command", {"op": "brightness", "level": value}) for value in (-1, 2, float("nan"))],
    ("run_macro", {}),
    ("run_macro", {"workflow": "a", "steps": []}),
    ("run_macro", {"steps": [], "params": {}}),
    *[
        ("run_macro", {"workflow": "a", "params": {"x": value}})
        for value in (None, [1], {"nested": 1})
    ],
    ("run_macro", {"steps": [{}]}),
    ("run_macro", {"steps": [{"action": 1}]}),
    ("run_macro", {"steps": [{"action": "tap"}] * 201}),
    ("run_agent", {"task": ""}),
    ("run_agent", {"task": "x" * 2001}),
]


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("name,kwargs", INVALID)
async def test_validation_before_request(
    mock_api: MockAPI, asynchronous: bool, name: str, kwargs: dict[str, Any]
) -> None:
    resource = mock_api.async_client.phones if asynchronous else mock_api.client.phones
    with pytest.raises(ValueError):
        result = getattr(resource, name)("phone-1", **kwargs)
        if asynchronous:
            await result
    assert mock_api.requests == []


def test_list_socket() -> None:
    operation = phones.list()
    assert operation.fun is not None and operation.fun.fun == "/app/phones/list"
    assert operation.fun.data == {}
    assert operation.parse_socket is not None
    assert operation.parse_socket([PHONE])[0].slot == "phone-1"
