import pytest

from tests.conftest import MockAPI
from zerobull._operations import session as session_ops

SESSION = {
    "phones": [
        {
            "id": "b3f00000-0000-0000-0000-000000000000",
            "name": "slot4",
            "video_live": True,
            "input_present": True,
            "can_control": True,
            "model": "iPhone 13",
            "os_version": "17.4",
        }
    ],
    "socket_url": "wss://0bull.net/farm-ws?t=short-lived-token",
    "ice_servers": [{"urls": ["stun:stun.example.com"], "username": "u", "credential": "c"}],
    "farm_online": True,
}


def test_create(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phone-controller", json=SESSION)
    result = mock_api.client.session.create()
    assert result.socket_url == SESSION["socket_url"]
    assert result.farm_online is True
    phone = result.phones[0]
    assert phone.slot == phone.id == "b3f00000-0000-0000-0000-000000000000"
    request = mock_api.requests[-1]
    assert request.method == "GET" and request.url.path == "/api/v1/phone-controller"


@pytest.mark.anyio
async def test_async_create(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/phone-controller", json=SESSION)
    result = await mock_api.async_client.session.create()
    assert result.phones[0].name == "slot4"


def test_no_socket_fun() -> None:
    op = session_ops.create()
    assert op.fun is None
