"""Public socket resource integration tests."""

import base64

import pytest

from zerobull import AsyncPage, AsyncSocket, Page, Socket
from zerobull.models import (
    Account,
    BillingRequest,
    BillingSummary,
    Phone,
    PhoneCountChange,
    Rental,
    Run,
    Submission,
    UploadURL,
)

from .conftest import MockAPI
from .socket_server import SocketServer, session_body
from .test_accounts import ACCOUNT
from .test_billing import CHANGE_APPLIED, RENTAL, REQUEST_STATUS, SUMMARY
from .test_phones import JPEG, PHONE, RUN
from .test_submissions import SUBMISSION, UPLOAD


def test_socket_context(mock_api: MockAPI) -> None:
    with SocketServer() as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        socket = mock_api.client.socket()
        assert isinstance(socket, Socket)
        assert not mock_api.requests
        with socket:
            assert socket.session.farm_online
            assert socket.call("/echo", {"value": 42}) == {"value": 42}
            assert list(socket.events(timeout=0.01)) == []
        assert list(socket.events()) == []


@pytest.mark.anyio
async def test_async_socket_context(mock_api: MockAPI) -> None:
    async with SocketServer() as server:
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        socket = mock_api.async_client.socket()
        assert isinstance(socket, AsyncSocket)
        assert not mock_api.requests
        async with socket:
            assert socket.session.farm_online
            assert await socket.call("/echo", {"value": 42}) == {"value": 42}
            assert [event async for event in socket.events(timeout=0.01)] == []
        assert [event async for event in socket.events()] == []


def page_body(item: object) -> dict[str, object]:
    return {"data": [item], "meta": {"current_page": 1, "last_page": 1, "per_page": 20, "total": 1}}


# Explicit wire expectations keep these tests independent of operation definitions.
CASES: list[
    tuple[str, str, tuple[object, ...], dict[str, object], str, dict[str, object], object, object]
] = [
    (
        "accounts",
        "list",
        (),
        {"page": 1},
        "/app/accounts/list",
        {"page": 1},
        page_body(ACCOUNT),
        [Account.model_validate(ACCOUNT)],
    ),
    (
        "accounts",
        "get",
        ("acc_1",),
        {},
        "/app/accounts/get",
        {"account": "acc_1"},
        ACCOUNT,
        Account.model_validate(ACCOUNT),
    ),
    (
        "accounts",
        "create",
        (),
        {"handle": "@me", "slot": "slot_1"},
        "/app/accounts/create",
        {"handle": "@me", "slot": "slot_1"},
        ACCOUNT,
        Account.model_validate(ACCOUNT),
    ),
    (
        "accounts",
        "update",
        ("acc_1",),
        {"handle": "@new"},
        "/app/accounts/update",
        {"account": "acc_1", "handle": "@new"},
        ACCOUNT,
        Account.model_validate(ACCOUNT),
    ),
    (
        "accounts",
        "delete",
        ("acc_1",),
        {},
        "/app/accounts/delete",
        {"account": "acc_1"},
        None,
        None,
    ),
    (
        "uploads",
        "create",
        (),
        {},
        "/app/submissions/upload-url",
        {},
        UPLOAD,
        UploadURL.model_validate(UPLOAD),
    ),
    (
        "submissions",
        "list",
        (),
        {},
        "/app/submissions/list",
        {},
        page_body(SUBMISSION),
        [Submission.model_validate(SUBMISSION)],
    ),
    (
        "submissions",
        "get",
        (1,),
        {},
        "/app/submissions/get",
        {"submission": 1},
        SUBMISSION,
        Submission.model_validate(SUBMISSION),
    ),
    (
        "submissions",
        "create",
        (),
        {"account_id": "acc_1", "video_url": "https://example.org/a.mp4", "draft": False},
        "/app/submissions/create",
        {"account": "acc_1", "video_url": "https://example.org/a.mp4", "draft": False},
        SUBMISSION,
        Submission.model_validate(SUBMISSION),
    ),
    (
        "submissions",
        "cancel",
        (1,),
        {},
        "/app/submissions/cancel",
        {"submission": 1},
        SUBMISSION,
        Submission.model_validate(SUBMISSION),
    ),
    ("submissions", "delete", (1,), {}, "/app/submissions/delete", {"submission": 1}, None, None),
    (
        "submissions",
        "wait",
        (1,),
        {},
        "/app/submissions/get",
        {"submission": 1},
        {**SUBMISSION, "status": "published"},
        Submission.model_validate({**SUBMISSION, "status": "published"}),
    ),
    ("phones", "list", (), {}, "/app/phones/list", {}, [PHONE], [Phone.model_validate(PHONE)]),
    (
        "phones",
        "snapshot",
        ("phone-1",),
        {"width": 600},
        "/app/phones/snapshot",
        {"slot": "phone-1", "width": 600},
        {"image": base64.b64encode(JPEG).decode(), "content_type": "image/jpeg"},
        JPEG,
    ),
    (
        "phones",
        "ocr",
        ("phone-1",),
        {},
        "/app/phones/ocr",
        {"slot": "phone-1"},
        {"text": "hello"},
        "hello",
    ),
    (
        "phones",
        "tap",
        ("phone-1",),
        {"fx": 0.5, "fy": 0.1},
        "/app/phones/input",
        {"slot": "phone-1", "op": "tap", "fx": 0.5, "fy": 0.1},
        {"op": "tap"},
        None,
    ),
    (
        "phones",
        "swipe",
        ("phone-1",),
        {"fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0},
        "/app/phones/input",
        {"slot": "phone-1", "op": "swipe", "fx1": 0, "fy1": 1, "fx2": 1, "fy2": 0},
        {"op": "swipe"},
        None,
    ),
    (
        "phones",
        "hotkey",
        ("phone-1", "home"),
        {},
        "/app/phones/input",
        {"slot": "phone-1", "op": "hotkey", "key": "home"},
        {"op": "hotkey"},
        None,
    ),
    (
        "phones",
        "type",
        ("phone-1", "hello"),
        {},
        "/app/phones/input",
        {"slot": "phone-1", "op": "type", "text": "hello"},
        {"op": "type"},
        None,
    ),
    (
        "phones",
        "run_command",
        ("phone-1", "wifi"),
        {"on": False},
        "/app/phones/commands",
        {"slot": "phone-1", "op": "wifi", "on": False},
        RUN,
        Run.model_validate(RUN),
    ),
    (
        "phones",
        "run_macro",
        ("phone-1",),
        {"workflow": "story"},
        "/app/phones/macros",
        {"slot": "phone-1", "workflow": "story"},
        RUN,
        Run.model_validate(RUN),
    ),
    (
        "phones",
        "run_agent",
        ("phone-1", "Open Settings"),
        {},
        "/app/phones/agent-runs",
        {"slot": "phone-1", "task": "Open Settings"},
        RUN,
        Run.model_validate(RUN),
    ),
    (
        "runs",
        "list",
        ("phone-1",),
        {},
        "/app/phones/runs",
        {"slot": "phone-1"},
        page_body(RUN),
        [Run.model_validate(RUN)],
    ),
    (
        "runs",
        "get",
        ("phone-1", "run-1"),
        {},
        "/app/phones/runs/get",
        {"slot": "phone-1", "run": "run-1"},
        RUN,
        Run.model_validate(RUN),
    ),
    (
        "runs",
        "wait",
        (Run.model_validate(RUN),),
        {},
        "/app/phones/runs/get",
        {"slot": "phone-1", "run": "run-1"},
        {**RUN, "status": "succeeded"},
        Run.model_validate({**RUN, "status": "succeeded"}),
    ),
    (
        "billing",
        "summary",
        (),
        {},
        "/app/billing/summary",
        {},
        SUMMARY,
        BillingSummary.model_validate(SUMMARY),
    ),
    (
        "billing",
        "start_rental",
        (),
        {"phones": 5, "country": "US", "accept_terms": True},
        "/app/billing/rentals",
        {"phones": 5, "country": "US", "accept_terms": True},
        RENTAL,
        Rental.model_validate(RENTAL),
    ),
    (
        "billing",
        "request_phone_count",
        (),
        {"add": 2, "accept_terms": True},
        "/app/billing/requests",
        {"add": 2, "accept_terms": True},
        CHANGE_APPLIED,
        PhoneCountChange.model_validate(CHANGE_APPLIED),
    ),
    (
        "billing",
        "get_request",
        ("request-1",),
        {},
        "/app/billing/requests/get",
        {"request_id": "request-1"},
        REQUEST_STATUS,
        BillingRequest.model_validate(REQUEST_STATUS),
    ),
]


@pytest.mark.parametrize("area,method,args,kwargs,fun,data,reply,expected", CASES)
def test_resources(
    mock_api: MockAPI,
    area: str,
    method: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
    fun: str,
    data: dict[str, object],
    reply: object,
    expected: object,
) -> None:
    with SocketServer() as server:
        server.replies[fun] = {"status": 204 if reply is None else 200, "data": reply}
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        with mock_api.client.socket() as socket:
            result = getattr(getattr(socket, area), method)(*args, **kwargs)
            if isinstance(result, Page):
                result = list(result.iter_all())
            assert result == expected
            assert server.frames[-1]["fun"] == fun
            assert server.frames[-1]["data"] == data
            assert not hasattr(socket, "user")


@pytest.mark.anyio
@pytest.mark.parametrize("area,method,args,kwargs,fun,data,reply,expected", CASES)
async def test_async_resources(
    mock_api: MockAPI,
    area: str,
    method: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
    fun: str,
    data: dict[str, object],
    reply: object,
    expected: object,
) -> None:
    async with SocketServer() as server:
        server.replies[fun] = {"status": 204 if reply is None else 200, "data": reply}
        mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
        async with mock_api.async_client.socket() as socket:
            result = await getattr(getattr(socket, area), method)(*args, **kwargs)
            if isinstance(result, AsyncPage):
                result = [item async for item in result.iter_all()]
            assert result == expected
            assert server.frames[-1]["fun"] == fun
            assert server.frames[-1]["data"] == data
            assert not hasattr(socket, "user")


def prepare_upload(mock_api: MockAPI, server: SocketServer) -> None:
    mock_api.add("GET", "/api/v1/phone-controller", json=session_body(server.url))
    mock_api.add("POST", "/signed", status=204)
    server.replies["/app/submissions/upload-url"] = {"status": 201, "data": UPLOAD}
    server.replies["/app/submissions/create"] = {"status": 201, "data": SUBMISSION}


def assert_upload(mock_api: MockAPI, server: SocketServer, submission: bool) -> None:
    request = mock_api.requests[-1]
    assert request.url == UPLOAD["upload_url"]
    assert "authorization" not in request.headers
    assert b"video-content" in request.content
    assert server.frames[0]["fun"] == "/app/submissions/upload-url"
    if submission:
        assert server.frames[1]["fun"] == "/app/submissions/create"
        assert server.frames[1]["data"] == {"account": "acc_1", "upload_id": "up_1"}


@pytest.mark.parametrize("submission", [False, True])
def test_upload_over_http(mock_api: MockAPI, submission: bool) -> None:
    with SocketServer() as server:
        prepare_upload(mock_api, server)
        with mock_api.client.socket() as socket:
            if submission:
                result = socket.submissions.create(account_id="acc_1", video=b"video-content")
                assert result == Submission.model_validate(SUBMISSION)
            else:
                assert socket.uploads.upload(b"video-content") == "up_1"
            assert_upload(mock_api, server, submission)


@pytest.mark.anyio
@pytest.mark.parametrize("submission", [False, True])
async def test_async_upload_over_http(mock_api: MockAPI, submission: bool) -> None:
    async with SocketServer() as server:
        prepare_upload(mock_api, server)
        async with mock_api.async_client.socket() as socket:
            if submission:
                result = await socket.submissions.create(account_id="acc_1", video=b"video-content")
                assert result == Submission.model_validate(SUBMISSION)
            else:
                assert await socket.uploads.upload(b"video-content") == "up_1"
            assert_upload(mock_api, server, submission)
