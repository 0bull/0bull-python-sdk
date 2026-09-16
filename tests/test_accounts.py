import pytest

from tests.conftest import MockAPI
from zerobull._operations import accounts as accounts_ops
from zerobull._operations._base import NOT_GIVEN, NotGiven, compact_given, parse_model_socket
from zerobull.models.accounts import Account

ACCOUNT: dict[str, object] = {
    "id": "acc_1",
    "platform": "tiktok",
    "handle": "@me",
    "slot": "slot_1",
    "notes": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}


def _page(items: list[dict[str, object]], current_page: int, last_page: int) -> dict[str, object]:
    return {
        "data": items,
        "meta": {"current_page": current_page, "last_page": last_page, "per_page": 1, "total": 2},
    }


def test_not_given() -> None:
    assert bool(NOT_GIVEN) is False
    assert repr(NOT_GIVEN) == "NOT_GIVEN"
    assert isinstance(NOT_GIVEN, NotGiven)
    assert compact_given({"a": NOT_GIVEN, "b": None, "c": 1}) == {"b": None, "c": 1}
    assert compact_given({}) == {}


def test_list_op() -> None:
    op = accounts_ops.list(page=2, platform="tiktok")
    assert op.rest is not None
    assert op.rest.method == "GET" and op.rest.path == "/v1/accounts"
    assert op.rest.params == {"page": 2, "platform": "tiktok"}
    assert op.fun is not None
    assert op.fun.fun == "/app/accounts/list" and op.fun.data == {"page": 2, "platform": "tiktok"}


def test_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/accounts", json=_page([ACCOUNT], 1, 2))
    page = mock_api.client.accounts.list(platform="tiktok")
    assert [account.id for account in page] == ["acc_1"]
    assert page.current_page == 1 and page.has_next_page
    assert mock_api.records[-1]["query"] == {"platform": "tiktok"}

    mock_api.add("GET", "/api/v1/accounts", json=_page([{**ACCOUNT, "id": "acc_2"}], 2, 2))
    all_items = list(page.iter_all())
    assert [account.id for account in all_items] == ["acc_1", "acc_2"]


@pytest.mark.anyio
async def test_async_list(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/accounts", json=_page([ACCOUNT], 1, 2))
    page = await mock_api.async_client.accounts.list()
    mock_api.add("GET", "/api/v1/accounts", json=_page([{**ACCOUNT, "id": "acc_2"}], 2, 2))
    assert [account.id async for account in page.iter_all()] == ["acc_1", "acc_2"]


def test_get(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/accounts/acc_1", json={"data": ACCOUNT})
    account = mock_api.client.accounts.get("acc_1")
    assert account.id == "acc_1" and account.handle == "@me"
    op = accounts_ops.get("acc_1")
    assert op.fun is not None
    assert op.fun.fun == "/app/accounts/get" and op.fun.data == {"account": "acc_1"}
    assert parse_model_socket(Account)(ACCOUNT).id == "acc_1"


@pytest.mark.anyio
async def test_async_get(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/accounts/acc_1", json={"data": ACCOUNT})
    assert (await mock_api.async_client.accounts.get("acc_1")).id == "acc_1"


def test_get_encodes_path_segment() -> None:
    op = accounts_ops.get("weird/id?x")
    assert op.rest is not None
    assert op.rest.path == "/v1/accounts/weird%2Fid%3Fx"


def test_create_validation() -> None:
    with pytest.raises(ValueError, match="slot"):
        accounts_ops.create(handle="@me")
    with pytest.raises(ValueError, match="slot"):
        accounts_ops.create(handle="@me", platform="tiktok")
    with pytest.raises(ValueError, match="google_email"):
        accounts_ops.create(handle="@me", platform="instagram", google_email="a@b.com")
    with pytest.raises(ValueError, match="google_email"):
        accounts_ops.create(handle="@me", platform="youtube")
    accounts_ops.create(handle="@me", platform="tiktok", slot="s1")
    accounts_ops.create(handle="@me", platform="instagram")
    accounts_ops.create(handle="@me", platform="youtube", google_email="a@b.com")


def test_create_op_socket() -> None:
    op = accounts_ops.create(handle="@me", platform="tiktok", slot="s1")
    assert op.fun is not None
    assert op.fun.fun == "/app/accounts/create"
    assert op.fun.data == {
        "platform": "tiktok",
        "handle": "@me",
        "slot": "s1",
        "notes": None,
        "google_email": None,
    }


def test_create(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/accounts", json={"data": ACCOUNT}, status=201)
    account = mock_api.client.accounts.create(handle="@me", platform="tiktok", slot="s1")
    assert account.id == "acc_1"
    assert mock_api.records[-1]["json"] == {"platform": "tiktok", "handle": "@me", "slot": "s1"}


@pytest.mark.anyio
async def test_async_create(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/accounts", json={"data": ACCOUNT}, status=201)
    account = await mock_api.async_client.accounts.create(
        handle="@me", platform="tiktok", slot="s1"
    )
    assert account.id == "acc_1"


def test_update_requires_a_field() -> None:
    with pytest.raises(ValueError, match="field"):
        accounts_ops.update("acc_1")


def test_update_op_sends_only_given_fields() -> None:
    op = accounts_ops.update("acc_1", slot=None)
    assert op.rest is not None
    assert op.rest.json == {"slot": None} and op.rest.compact_json is False
    assert op.fun is not None
    assert op.fun.data == {"account": "acc_1", "slot": None}
    assert op.fun.compact is False

    op2 = accounts_ops.update("acc_1", handle="new")
    assert op2.rest is not None and op2.rest.json == {"handle": "new"}


def test_update_sends_only_passed_fields(mock_api: MockAPI) -> None:
    mock_api.add("PUT", "/api/v1/accounts/acc_1", json={"data": {**ACCOUNT, "handle": "new"}})
    account = mock_api.client.accounts.update("acc_1", handle="new")
    assert account.handle == "new"
    assert mock_api.records[-1]["json"] == {"handle": "new"}


def test_update_clears_a_field_with_null(mock_api: MockAPI) -> None:
    mock_api.add("PUT", "/api/v1/accounts/acc_1", json={"data": {**ACCOUNT, "slot": None}})
    account = mock_api.client.accounts.update("acc_1", slot=None)
    assert account.slot is None
    assert mock_api.records[-1]["json"] == {"slot": None}


@pytest.mark.anyio
async def test_async_update(mock_api: MockAPI) -> None:
    mock_api.add("PUT", "/api/v1/accounts/acc_1", json={"data": {**ACCOUNT, "slot": None}})
    account = await mock_api.async_client.accounts.update("acc_1", slot=None)
    assert account.slot is None
    assert mock_api.records[-1]["json"] == {"slot": None}
    with pytest.raises(ValueError, match="field"):
        await mock_api.async_client.accounts.update("acc_1")


def test_delete(mock_api: MockAPI) -> None:
    mock_api.add("DELETE", "/api/v1/accounts/acc_1", status=204)
    mock_api.client.accounts.delete("acc_1")
    assert mock_api.requests[-1].method == "DELETE"
    op = accounts_ops.delete("acc_1")
    assert op.fun is not None
    assert op.fun.fun == "/app/accounts/delete" and op.fun.data == {"account": "acc_1"}


@pytest.mark.anyio
async def test_async_delete(mock_api: MockAPI) -> None:
    mock_api.add("DELETE", "/api/v1/accounts/acc_1", status=204)
    await mock_api.async_client.accounts.delete("acc_1")
