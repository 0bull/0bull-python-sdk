import pytest

from zerobull._pagination import AsyncPage, Page, PageData


def test_pages() -> None:
    def fetch(number: int) -> Page[int]:
        return Page(PageData([number], number, 2, 1, 2), fetch)

    page = fetch(1)
    assert list(page) == [1]
    assert len(page) == 1 and page[0] == 1 and page[:] == [1]
    assert page.has_next_page and page.per_page == 1 and page.total == 2
    assert list(page.iter_all()) == [1, 2]
    assert fetch(2).next_page() is None


@pytest.mark.anyio
async def test_async_pages() -> None:
    async def fetch(number: int) -> AsyncPage[int]:
        return AsyncPage(PageData([number], number, 2, 1, 2), fetch)

    page = await fetch(1)
    assert list(page) == [1] and len(page) == 1 and page[0] == 1
    assert [item async for item in page.iter_all()] == [1, 2]
    assert await (await fetch(2)).next_page() is None


def test_page_parsers() -> None:
    import json

    from tests.test_user import USER
    from zerobull._operations._base import RestResponse, parse_page, parse_page_socket
    from zerobull.models.user import User

    meta = {"current_page": 1, "last_page": 2, "per_page": 1, "total": 2}
    body = {"data": [USER], "meta": meta}
    socket = parse_page_socket(User)(body)
    rest = parse_page(User)(
        RestResponse(
            200,
            {},
            json.dumps({**body, "meta": {**meta, "links": [], "path": "/api/user"}}).encode(),
        )
    )
    assert rest == socket and rest.items[0].id == 1
    invalid_bodies: tuple[object, ...] = (None, {}, {"data": {}})
    for bad in invalid_bodies:
        with pytest.raises(ValueError):
            parse_page_socket(User)(bad)
        with pytest.raises(ValueError):
            parse_page(User)(RestResponse(200, {}, json.dumps(bad).encode()))
