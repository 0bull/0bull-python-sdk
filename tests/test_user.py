from pathlib import Path

import pytest

from tests.conftest import MockAPI
from zerobull._operations import user
from zerobull._operations._base import RestResponse, parse_model_socket
from zerobull.models.user import User

USER = {"id": 1, "name": "Test", "email": "test@example.com", "email_verified_at": None}


def test_user(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/user", json={"data": USER})
    assert mock_api.client.user.get().id == 1
    assert user.get().fun is None
    assert parse_model_socket(User)(USER).name == "Test"
    assert RestResponse(204, {}, b"").json() is None


@pytest.mark.anyio
async def test_async_user(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/user", json={"data": USER})
    assert (await mock_api.async_client.user.get()).id == 1


def test_model_validation_and_unknown_fields() -> None:
    import pydantic

    model = parse_model_socket(User)({**USER, "future": "kept"})
    assert model.model_extra == {"future": "kept"}
    with pytest.raises(pydantic.ValidationError):
        model.__setattr__("name", "changed")
    with pytest.raises(pydantic.ValidationError):
        parse_model_socket(User)({"id": "bad"})


def test_operation_helpers(tmp_path: Path) -> None:
    import io

    from zerobull._operations._base import (
        compact,
        path_segment,
        require_range,
        to_file_content,
        unwrap,
    )

    assert compact({"none": None, "false": False, "nested": {"none": None}}) == {
        "false": False,
        "nested": {"none": None},
    }
    assert compact(None) == {}
    assert path_segment("acc_1") == "acc_1"
    assert path_segment("weird/id?x") == "weird%2Fid%3Fx"
    for value in (None, 0, 1):
        require_range("x", value, 0, 1)
    for invalid in (-1, 2, float("nan")):
        with pytest.raises(ValueError, match="x"):
            require_range("x", invalid, 0, 1)
    with pytest.raises(ValueError, match="data"):
        unwrap(RestResponse(200, {}, b"{}"))
    for suffix, mime in (
        (".mp4", "video/mp4"),
        (".MOV", "video/quicktime"),
        (".bin", "application/octet-stream"),
    ):
        path = tmp_path / f"clip{suffix}"
        path.write_bytes(b"video")
        name, stream, content_type = to_file_content(path)
        assert name == path.name and content_type == mime
        assert not isinstance(stream, bytes)
        with stream:
            assert stream.read() == b"video"
        with path.open("rb") as handle:
            assert to_file_content(handle) == (path.name, handle, mime)
    raw = io.BytesIO(b"video")
    assert to_file_content(raw) == ("video", raw, "application/octet-stream")
    assert to_file_content(b"video") == ("video", b"video", "application/octet-stream")
