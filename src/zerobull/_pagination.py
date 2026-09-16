"""Page-local iteration and explicit traversal across pages."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar, overload

M = TypeVar("M")


@dataclass(frozen=True)
class PageData(Generic[M]):
    """Parsed items and pagination metadata."""

    items: list[M]
    current_page: int
    last_page: int
    per_page: int
    total: int


class _PageItems(Sequence[M]):
    def __init__(self, data: PageData[M]) -> None:
        self.items = data.items
        self.current_page = data.current_page
        self.last_page = data.last_page
        self.per_page = data.per_page
        self.total = data.total

    def __iter__(self) -> Iterator[M]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    @overload
    def __getitem__(self, index: int) -> M: ...
    @overload
    def __getitem__(self, index: slice) -> list[M]: ...
    def __getitem__(self, index: int | slice) -> M | list[M]:
        return self.items[index]

    @property
    def has_next_page(self) -> bool:
        """Whether another page follows this one."""
        return self.current_page < self.last_page


class Page(_PageItems[M]):
    """A page whose next page is fetched synchronously."""

    def __init__(self, data: PageData[M], fetch: Callable[[int], Page[M]]) -> None:
        super().__init__(data)
        self._fetch = fetch

    def next_page(self) -> Page[M] | None:
        """Fetch the next page, or return None at the end."""
        return self._fetch(self.current_page + 1) if self.has_next_page else None

    def iter_all(self) -> Iterator[M]:
        """Yield items from this page and every subsequent page."""
        page: Page[M] | None = self
        while page is not None:
            yield from page
            page = page.next_page()


class AsyncPage(_PageItems[M]):
    """A page whose next page is fetched asynchronously."""

    def __init__(self, data: PageData[M], fetch: Callable[[int], Awaitable[AsyncPage[M]]]) -> None:
        super().__init__(data)
        self._fetch = fetch

    async def next_page(self) -> AsyncPage[M] | None:
        """Fetch the next page, or return None at the end."""
        return await self._fetch(self.current_page + 1) if self.has_next_page else None

    async def iter_all(self) -> AsyncIterator[M]:
        """Yield items from this page and every subsequent page."""
        page: AsyncPage[M] | None = self
        while page is not None:
            for item in page:
                yield item
            page = await page.next_page()
