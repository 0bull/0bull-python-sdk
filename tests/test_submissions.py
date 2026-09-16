from pathlib import Path
from typing import Any, BinaryIO, cast

import httpx
import pytest

from tests.conftest import MockAPI
from zerobull._config import ClientOptions
from zerobull._errors import ValidationError, WaitTimeoutError
from zerobull._operations import submissions as submissions_ops
from zerobull._operations._base import Operation, parse_model_socket
from zerobull._transport.http import AsyncHTTPTransport, SyncHTTPTransport
from zerobull.models.submissions import TERMINAL_SUBMISSION_STATUSES, Submission
from zerobull.models.uploads import UploadURL
from zerobull.resources.submissions import AsyncSubmissions, Submissions

SUBMISSION = {
    "id": 1,
    "platform": "tiktok",
    "account_id": "acc_1",
    "caption": "hi",
    "draft": False,
    "status": "pending",
    "attempts": 0,
    "failure": None,
    "started_at": None,
    "finished_at": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}

UPLOAD = {
    "upload_id": "up_1",
    "upload_url": "https://upload.example/signed",
    "expires_at": "2024-01-01T00:00:00Z",
}


def _page(items: list[dict[str, object]], current_page: int, last_page: int) -> dict[str, object]:
    return {
        "data": items,
        "meta": {"current_page": current_page, "last_page": last_page, "per_page": 1, "total": 1},
    }


def test_model_is_terminal() -> None:
    for status in TERMINAL_SUBMISSION_STATUSES:
        assert Submission.model_validate({**SUBMISSION, "status": status}).is_terminal
    assert not Submission.model_validate({**SUBMISSION, "status": "pending"}).is_terminal


def test_list_op() -> None:
    op = submissions_ops.list(page=1, platform="tiktok")
    assert op.rest is not None and op.rest.path == "/v1/submissions"
    assert op.fun is not None
    assert op.fun.fun == "/app/submissions/list" and op.fun.data == {
        "page": 1,
        "platform": "tiktok",
    }


def test_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/submissions", json=_page([SUBMISSION], 1, 1))
    page = mock_api.client.submissions.list()
    assert [item.id for item in page] == [1]
    assert page.next_page() is None


@pytest.mark.anyio
async def test_async_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/submissions", json=_page([SUBMISSION], 1, 2))
    page = await mock_api.async_client.submissions.list()
    mock_api.add("GET", "/api/v1/submissions", json=_page([{**SUBMISSION, "id": 2}], 2, 2))
    assert [item.id async for item in page.iter_all()] == [1, 2]


def test_get(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/submissions/1", json={"data": SUBMISSION})
    submission = mock_api.client.submissions.get(1)
    assert submission.id == 1
    op = submissions_ops.get(1)
    assert op.fun is not None
    assert op.fun.fun == "/app/submissions/get" and op.fun.data == {"submission": 1}
    assert parse_model_socket(Submission)(SUBMISSION).id == 1


@pytest.mark.anyio
async def test_async_get(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/submissions/1", json={"data": SUBMISSION})
    assert (await mock_api.async_client.submissions.get(1)).id == 1


def test_create_validation() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        submissions_ops.create(account_id="acc_1", caption="hi")
    with pytest.raises(ValueError, match="Exactly one"):
        submissions_ops.create(
            account_id="acc_1", video_url="https://x/v.mp4", upload_id="up_1", caption="hi"
        )
    with pytest.raises(ValueError, match="2200"):
        submissions_ops.create(account_id="acc_1", video_url="https://x/v.mp4", caption="a" * 2201)
    with pytest.raises(ValueError, match="required"):
        submissions_ops.create(account_id="acc_1", video_url="https://x/v.mp4", platform="youtube")
    with pytest.raises(ValueError, match="100"):
        submissions_ops.create(
            account_id="acc_1",
            video_url="https://x/v.mp4",
            platform="youtube",
            caption="a" * 101,
        )
    submissions_ops.create(account_id="acc_1", video_url="https://x/v.mp4")
    submissions_ops.create(
        account_id="acc_1", video_url="https://x/v.mp4", platform="youtube", caption="title"
    )


def test_create_op_video_disables_socket() -> None:
    op = submissions_ops.create(account_id="acc_1", video=b"clip", caption="hi")
    assert op.fun is None
    assert op.rest is not None
    assert op.rest.files is None
    assert op.rest.file == ("video", b"clip")

    op2 = submissions_ops.create(account_id="acc_1", upload_id="up_1", caption="hi")
    assert op2.fun is not None
    assert op2.fun.fun == "/app/submissions/create"
    assert op2.fun.data == {
        "platform": None,
        "account": "acc_1",
        "video_url": None,
        "upload_id": "up_1",
        "caption": "hi",
        "draft": None,
    }


def test_create_video_url(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/submissions", json={"data": SUBMISSION}, status=201)
    submission = mock_api.client.submissions.create(
        account_id="acc_1", video_url="https://x/video.mp4", caption="hi"
    )
    assert submission.id == 1
    record = mock_api.records[-1]
    assert record["data"] == {
        "account_id": "acc_1",
        "video_url": "https://x/video.mp4",
        "caption": "hi",
    }
    assert record["files"] == {}


def test_create_video_file(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/submissions", json={"data": SUBMISSION}, status=201)
    mock_api.client.submissions.create(account_id="acc_1", video=b"clip", caption="hi")
    record = mock_api.records[-1]
    assert record["data"] == {"account_id": "acc_1", "caption": "hi"}
    assert record["files"] == {
        "video": {
            "filename": "video",
            "content": b"clip",
            "content_type": "application/octet-stream",
        }
    }


@pytest.fixture
def tracked_opens(monkeypatch: pytest.MonkeyPatch) -> list[BinaryIO]:
    """Record every file handle opened via Path.open("rb") for the test's duration."""
    opened: list[BinaryIO] = []
    original_open = Path.open

    def spy_open(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> BinaryIO:
        handle = cast(BinaryIO, original_open(self, mode, *args, **kwargs))
        opened.append(handle)
        return handle

    monkeypatch.setattr(Path, "open", spy_open)
    return opened


def test_create_video_path_closes_on_success(
    mock_api: MockAPI, tmp_path: Path, tracked_opens: list[BinaryIO]
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    mock_api.add("POST", "/api/v1/submissions", json={"data": SUBMISSION}, status=201)
    mock_api.client.submissions.create(account_id="acc_1", video=video, caption="hi")
    assert tracked_opens and all(handle.closed for handle in tracked_opens)


def test_create_video_path_closes_on_error(
    mock_api: MockAPI, tmp_path: Path, tracked_opens: list[BinaryIO]
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    mock_api.add("POST", "/api/v1/submissions", json={"message": "bad", "errors": {}}, status=422)
    with pytest.raises(ValidationError):
        mock_api.client.submissions.create(account_id="acc_1", video=video, caption="hi")
    assert tracked_opens and all(handle.closed for handle in tracked_opens)


def test_socket_create_with_video_path_closes(
    mock_api: MockAPI, tmp_path: Path, tracked_opens: list[BinaryIO]
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    mock_api.add("POST", "/signed", json={"ok": True})
    fake = _FakeSocketTransport()
    resource = Submissions(fake, mock_api.client._http)
    resource.create(account_id="acc_1", video=video, caption="hi")
    assert tracked_opens and all(handle.closed for handle in tracked_opens)


@pytest.mark.anyio
async def test_async_create_video_path_closes(
    mock_api: MockAPI, tmp_path: Path, tracked_opens: list[BinaryIO]
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    mock_api.add("POST", "/api/v1/submissions", json={"data": SUBMISSION}, status=201)
    await mock_api.async_client.submissions.create(account_id="acc_1", video=video, caption="hi")
    assert tracked_opens and all(handle.closed for handle in tracked_opens)


@pytest.mark.anyio
async def test_async_create(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/submissions", json={"data": SUBMISSION}, status=201)
    submission = await mock_api.async_client.submissions.create(
        account_id="acc_1", video_url="https://x/video.mp4", caption="hi"
    )
    assert submission.id == 1


def test_cancel(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/submissions/1/cancel", json={"data": SUBMISSION})
    assert mock_api.client.submissions.cancel(1).id == 1
    op = submissions_ops.cancel(1)
    assert op.fun is not None
    assert op.fun.fun == "/app/submissions/cancel" and op.fun.data == {"submission": 1}


@pytest.mark.anyio
async def test_async_cancel(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/submissions/1/cancel", json={"data": SUBMISSION})
    assert (await mock_api.async_client.submissions.cancel(1)).id == 1


def test_delete(mock_api: MockAPI) -> None:
    mock_api.add("DELETE", "/api/v1/submissions/1", status=204)
    mock_api.client.submissions.delete(1)
    op = submissions_ops.delete(1)
    assert op.fun is not None
    assert op.fun.fun == "/app/submissions/delete" and op.fun.data == {"submission": 1}


@pytest.mark.anyio
async def test_async_delete(mock_api: MockAPI) -> None:
    mock_api.add("DELETE", "/api/v1/submissions/1", status=204)
    await mock_api.async_client.submissions.delete(1)


class _FakeSocketTransport:
    """Records executed operations; never touches HTTP."""

    supports_rest = False

    def __init__(self) -> None:
        self.executed: list[Operation[Any]] = []

    def execute(self, operation: Operation[Any]) -> Any:
        self.executed.append(operation)
        if operation.fun is not None and operation.fun.fun == "/app/submissions/upload-url":
            return UploadURL.model_validate(UPLOAD)
        return Submission.model_validate(SUBMISSION)


class _AsyncFakeSocketTransport(_FakeSocketTransport):
    async def execute(self, operation: Operation[Any]) -> Any:
        return super().execute(operation)


def test_socket_create_with_video_uploads_first(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/signed", json={"ok": True})
    fake = _FakeSocketTransport()
    resource = Submissions(fake, mock_api.client._http)

    submission = resource.create(account_id="acc_1", video=b"clip", caption="hi")

    assert submission.id == 1
    assert len(fake.executed) == 2
    upload_op, create_op = fake.executed
    assert upload_op.fun is not None and upload_op.fun.fun == "/app/submissions/upload-url"
    assert create_op.fun is not None and create_op.fun.fun == "/app/submissions/create"
    assert create_op.fun.data == {
        "platform": None,
        "account": "acc_1",
        "video_url": None,
        "upload_id": "up_1",
        "caption": "hi",
        "draft": None,
    }
    assert "authorization" not in mock_api.requests[-1].headers


@pytest.mark.anyio
async def test_async_socket_create_with_video_uploads_first(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/signed", json={"ok": True})
    fake = _AsyncFakeSocketTransport()
    resource = AsyncSubmissions(fake, mock_api.async_client._http)

    submission = await resource.create(account_id="acc_1", video=b"clip", caption="hi")

    assert submission.id == 1
    assert len(fake.executed) == 2
    create_fun = fake.executed[1].fun
    assert create_fun is not None and create_fun.data is not None
    assert create_fun.data["upload_id"] == "up_1"


def test_socket_create_with_video_and_upload_id_raises_before_upload(mock_api: MockAPI) -> None:
    fake = _FakeSocketTransport()
    resource = Submissions(fake, mock_api.client._http)

    with pytest.raises(ValueError, match="Exactly one"):
        resource.create(account_id="acc_1", video=b"clip", upload_id="up_1", caption="hi")

    assert fake.executed == []


def test_socket_create_with_video_and_video_url_raises_before_upload(mock_api: MockAPI) -> None:
    fake = _FakeSocketTransport()
    resource = Submissions(fake, mock_api.client._http)

    with pytest.raises(ValueError, match="Exactly one"):
        resource.create(
            account_id="acc_1", video=b"clip", video_url="https://x/v.mp4", caption="hi"
        )

    assert fake.executed == []


@pytest.mark.anyio
async def test_async_socket_create_with_video_and_upload_id_raises_before_upload(
    mock_api: MockAPI,
) -> None:
    fake = _AsyncFakeSocketTransport()
    resource = AsyncSubmissions(fake, mock_api.async_client._http)

    with pytest.raises(ValueError, match="Exactly one"):
        await resource.create(account_id="acc_1", video=b"clip", upload_id="up_1", caption="hi")

    assert fake.executed == []


def test_wait_success(no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "published" if calls["n"] >= 2 else "pending"
        return httpx.Response(200, json={"data": {**SUBMISSION, "status": status}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = SyncHTTPTransport(ClientOptions("test"), client)
        result = Submissions(http, http).wait(1, interval=0, timeout=5)
    assert result.status == "published"
    assert no_sleep == [0]


def test_wait_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": SUBMISSION})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = SyncHTTPTransport(ClientOptions("test"), client)
        with pytest.raises(WaitTimeoutError, match="submission 1"):
            Submissions(http, http).wait(1, interval=1, timeout=0)


@pytest.mark.anyio
async def test_async_wait_success(no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "published" if calls["n"] >= 2 else "pending"
        return httpx.Response(200, json={"data": {**SUBMISSION, "status": status}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = AsyncHTTPTransport(ClientOptions("test"), client)
        result = await AsyncSubmissions(http, http).wait(
            Submission.model_validate(SUBMISSION), interval=0, timeout=5
        )
    assert result.status == "published"


@pytest.mark.anyio
async def test_async_wait_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": SUBMISSION})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = AsyncHTTPTransport(ClientOptions("test"), client)
        with pytest.raises(WaitTimeoutError, match="submission 1"):
            await AsyncSubmissions(http, http).wait(1, interval=1, timeout=0)
