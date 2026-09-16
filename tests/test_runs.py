from typing import Any

import pytest

from tests.conftest import MockAPI
from tests.test_phones import RUN
from zerobull._errors import WaitTimeoutError
from zerobull._operations import runs
from zerobull.models.runs import Run


def page(number: int) -> dict[str, Any]:
    return {
        "data": [{**RUN, "id": f"run-{number}"}],
        "meta": {"current_page": number, "last_page": 2, "per_page": 20, "total": 2},
    }


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_get(mock_api: MockAPI, asynchronous: bool) -> None:
    mock_api.add("GET", "/api/v1/phones/phone-1/runs/run-1", json={"data": RUN})
    result = (
        await mock_api.async_client.runs.get("phone-1", "run-1")
        if asynchronous
        else mock_api.client.runs.get("phone-1", "run-1")
    )
    assert result == Run.model_validate(RUN)
    assert mock_api.records[-1]["query"] == {}
    assert mock_api.records[-1]["json"] is None
    operation = runs.get("phone-1", "run-1")
    assert operation.fun is not None
    assert operation.fun.fun == "/app/phones/runs/get"
    assert operation.fun.data == {"slot": "phone-1", "run": "run-1"}
    assert operation.parse_socket is not None
    assert operation.parse_socket(RUN) == result


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_pagination(mock_api: MockAPI, asynchronous: bool) -> None:
    mock_api.add("GET", "/api/v1/phones/phone-1/runs", json=page(1))
    if asynchronous:
        first = await mock_api.async_client.runs.list("phone-1")
        mock_api.add("GET", "/api/v1/phones/phone-1/runs", json=page(2))
        assert [run.id async for run in first.iter_all()] == ["run-1", "run-2"]
    else:
        first_sync = mock_api.client.runs.list("phone-1")
        mock_api.add("GET", "/api/v1/phones/phone-1/runs", json=page(2))
        assert [run.id for run in first_sync.iter_all()] == ["run-1", "run-2"]
    assert [record["query"] for record in mock_api.records] == [{}, {"page": "2"}]
    assert all(record["json"] is None for record in mock_api.records)
    operation = runs.list("phone-1", page=2)
    assert operation.fun is not None and operation.fun.fun == "/app/phones/runs"
    assert operation.fun.data == {"slot": "phone-1", "page": 2}
    assert operation.parse_socket is not None
    parsed = operation.parse_socket(page(2))
    assert parsed.items[0].id == "run-2"
    assert (parsed.current_page, parsed.last_page, parsed.per_page, parsed.total) == (2, 2, 20, 2)


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_wait(
    mock_api: MockAPI, asynchronous: bool, no_sleep: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio
    import time

    path = "/api/v1/phones/phone-1/runs/run-1"
    mock_api.add("GET", path, json={"data": RUN})
    finished = {**RUN, "status": "succeeded", "result": {"text": "done"}}

    def finish(delay: float) -> None:
        no_sleep.append(delay)
        mock_api.add("GET", path, json={"data": finished})

    async def async_finish(delay: float) -> None:
        finish(delay)

    monkeypatch.setattr(time, "sleep", finish)
    monkeypatch.setattr(asyncio, "sleep", async_finish)
    run = Run.model_validate(RUN)
    result = (
        await mock_api.async_client.runs.wait(run, interval=0.5)
        if asynchronous
        else mock_api.client.runs.wait(run, interval=0.5)
    )
    assert result.succeeded and result.result == {"text": "done"}
    assert no_sleep == [0.5]
    assert len(mock_api.requests) == 2
    mock_api.add("GET", path, json={"data": RUN})
    with pytest.raises(WaitTimeoutError):
        if asynchronous:
            await mock_api.async_client.runs.wait(run, timeout=0)
        else:
            mock_api.client.runs.wait(run, timeout=0)
    assert no_sleep == [0.5]


@pytest.mark.parametrize(
    "status,terminal,success",
    [
        ("queued", False, False),
        ("running", False, False),
        ("succeeded", True, True),
        ("failed", True, False),
        ("cancelled", True, False),
        ("future", False, False),
    ],
)
def test_run_status(status: str, terminal: bool, success: bool) -> None:
    run = Run.model_validate({**RUN, "status": status, "kind": "future", "future": 1})
    assert run.is_terminal is terminal and run.succeeded is success
    assert run.model_extra == {"future": 1}


@pytest.mark.anyio
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_invalid_page(mock_api: MockAPI, asynchronous: bool) -> None:
    with pytest.raises(ValueError):
        if asynchronous:
            await mock_api.async_client.runs.list("phone-1", page=0)
        else:
            mock_api.client.runs.list("phone-1", page=0)
    assert mock_api.requests == []
