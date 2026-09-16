import httpx
import pytest

from zerobull import AsyncZeroBull, ZeroBull, ZeroBullError
from zerobull._config import ClientOptions


def test_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZEROBULL_API_TOKEN", raising=False)
    with pytest.raises(ZeroBullError, match="token"):
        ZeroBull()
    monkeypatch.setenv("ZEROBULL_API_TOKEN", "env")
    monkeypatch.setenv("ZEROBULL_BASE_URL", "https://example.com/api/")
    options = ClientOptions()
    assert options.api_token == "env" and options.base_url == "https://example.com/api"
    assert ClientOptions("explicit", base_url="https://test/api").api_token == "explicit"
    assert "env" not in repr(options)


def test_contexts() -> None:
    with ZeroBull("test") as client:
        assert all(
            hasattr(client, area)
            for area in (
                "user",
                "accounts",
                "uploads",
                "submissions",
                "phones",
                "runs",
                "billing",
                "session",
            )
        )
    assert client._http._client.is_closed
    with httpx.Client() as http:
        with ZeroBull("test", http_client=http):
            pass
        assert not http.is_closed


@pytest.mark.anyio
async def test_async_contexts() -> None:
    async with AsyncZeroBull("test") as client:
        assert client.user is not None
    assert client._http._client.is_closed
    async with httpx.AsyncClient() as http:
        async with AsyncZeroBull("test", http_client=http):
            pass
        assert not http.is_closed
