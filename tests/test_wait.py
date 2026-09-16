import pytest

from zerobull._errors import WaitTimeoutError
from zerobull._wait import await_until, wait_until


def test_wait() -> None:
    values = iter([0, 1])
    assert (
        wait_until(
            lambda: next(values), bool, interval=0, timeout=1, what="run", sleep=lambda _: None
        )
        == 1
    )
    with pytest.raises(WaitTimeoutError, match="run"):
        wait_until(lambda: 0, bool, interval=0, timeout=0, what="run")


@pytest.mark.anyio
async def test_async_wait() -> None:
    values = iter([0, 1])

    async def fetch() -> int:
        return next(values)

    async def sleep(seconds: float) -> None:
        pass

    assert await await_until(fetch, bool, interval=0, timeout=1, what="run", sleep=sleep) == 1

    async def pending() -> int:
        return 0

    with pytest.raises(WaitTimeoutError, match="run"):
        await await_until(pending, bool, interval=0, timeout=0, what="run")
