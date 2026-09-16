from pathlib import Path

import pytest

from tests.conftest import MockAPI
from tests.test_submissions import UPLOAD
from zerobull._operations import uploads as uploads_ops
from zerobull._operations._base import parse_model_socket
from zerobull.models.uploads import UploadURL


def test_create_op() -> None:
    op = uploads_ops.create()
    assert op.rest is not None and op.rest.method == "POST" and op.rest.path == "/v1/uploads"
    assert op.fun is not None
    assert op.fun.fun == "/app/submissions/upload-url" and op.fun.data is None
    assert parse_model_socket(UploadURL)(UPLOAD).upload_id == "up_1"


def test_create_not_wrapped(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    result = mock_api.client.uploads.create()
    assert result.upload_id == "up_1" and result.upload_url == UPLOAD["upload_url"]


@pytest.mark.anyio
async def test_async_create(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    result = await mock_api.async_client.uploads.create()
    assert result.upload_id == "up_1"


def test_upload_bytes(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    mock_api.add("POST", "/signed", json={"ok": True})
    upload_id = mock_api.client.uploads.upload(b"video-bytes")
    assert upload_id == "up_1"
    assert [record["path"] for record in mock_api.records] == ["/api/v1/uploads", "/signed"]
    assert "authorization" not in mock_api.requests[-1].headers


def test_upload_path(mock_api: MockAPI, tmp_path: Path) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    mock_api.add("POST", "/signed", json={"ok": True})
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    assert mock_api.client.uploads.upload(video) == "up_1"
    assert mock_api.records[-1]["files"] == {
        "video": {"filename": "clip.mp4", "content": b"clip", "content_type": "video/mp4"}
    }


@pytest.mark.anyio
async def test_async_upload(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    mock_api.add("POST", "/signed", json={"ok": True})
    upload_id = await mock_api.async_client.uploads.upload(b"video-bytes")
    assert upload_id == "up_1"
    assert "authorization" not in mock_api.requests[-1].headers


@pytest.mark.anyio
async def test_async_upload_path(mock_api: MockAPI, tmp_path: Path) -> None:
    mock_api.add("POST", "/api/v1/uploads", json=UPLOAD, status=201)
    mock_api.add("POST", "/signed", json={"ok": True})
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    assert await mock_api.async_client.uploads.upload(video) == "up_1"
    assert mock_api.records[-1]["files"] == {
        "video": {"filename": "clip.mp4", "content": b"clip", "content_type": "video/mp4"}
    }
