"""Shared mock REST API; register routes with mock_api.add()."""

from __future__ import annotations

import asyncio
import json as json_module
import time
from collections.abc import Iterator, Mapping
from email import policy
from email.parser import BytesParser
from typing import cast

import httpx
import pytest

from zerobull import AsyncZeroBull, ZeroBull


class MockAPI:
    """Sync and async clients sharing registered routes and captured requests."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], httpx.Response] = {}
        self.requests: list[httpx.Request] = []
        self.records: list[dict[str, object]] = []
        transport = httpx.MockTransport(self._handle)
        self.http = httpx.Client(transport=transport)
        self.async_http = httpx.AsyncClient(transport=transport)
        self.client = ZeroBull("test", http_client=self.http)
        self.async_client = AsyncZeroBull("test", http_client=self.async_http)

    def add(
        self,
        method: str,
        path: str,
        *,
        json: object = None,
        status: int = 200,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Register or replace a response for a method and absolute URL path."""
        self.routes[(method.upper(), path)] = httpx.Response(
            status, json=json, content=content, headers=headers
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        fields: dict[str, str] = {}
        files: dict[str, dict[str, object]] = {}
        content_type = request.headers.get("content-type", "")
        body: object = None
        if "application/json" in content_type:
            body = json_module.loads(request.content)
        if "multipart/form-data" in content_type:
            message = BytesParser(policy=policy.default).parsebytes(
                f"Content-Type: {content_type}\r\n\r\n".encode() + request.content
            )
            for part in message.walk():
                name = part.get_param("name", header="content-disposition")
                if not isinstance(name, str):
                    continue
                payload = cast(bytes, part.get_payload(decode=True))
                if part.get_filename() is not None:
                    files[name] = {
                        "filename": part.get_filename(),
                        "content": payload,
                        "content_type": part.get_content_type(),
                    }
                else:
                    fields[name] = payload.decode()
        self.records.append(
            {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.url.params),
                "headers": dict(request.headers),
                "json": body,
                "data": fields,
                "files": files,
            }
        )
        response = self.routes[(request.method, request.url.path)]
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )


@pytest.fixture
def mock_api() -> Iterator[MockAPI]:
    api = MockAPI()
    yield api
    api.http.close()
    asyncio.run(api.async_http.aclose())


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record retry/poll delays without sleeping."""
    delays: list[float] = []

    async def async_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(time, "sleep", delays.append)
    monkeypatch.setattr(asyncio, "sleep", async_sleep)
    return delays
