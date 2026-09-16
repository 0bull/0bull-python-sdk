"""HTTP execution with bounded rate-limit retries."""

from __future__ import annotations

import asyncio
import io
import math
import time
from typing import BinaryIO, TypeVar

import httpx

from .._config import ClientOptions
from .._errors import APIConnectionError, APITimeoutError, error_from_status
from .._operations._base import (
    FileContent,
    Operation,
    RestRequest,
    RestResponse,
    compact,
    to_file_content,
)
from .._version import __version__

T = TypeVar("T")


def _retry_after(response: httpx.Response) -> float:
    try:
        delay = float(response.headers.get("Retry-After", "1"))
    except ValueError:
        return 1.0
    return min(delay, 60.0) if math.isfinite(delay) and delay >= 0 else 1.0


def _body(response: httpx.Response) -> object:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _check(response: httpx.Response) -> RestResponse:
    if not 200 <= response.status_code < 300:
        raise error_from_status(
            response.status_code,
            _body(response),
            _retry_after(response) if response.status_code == 429 else None,
        )
    return RestResponse(response.status_code, response.headers, response.content)


def _request(options: ClientOptions, rest: RestRequest) -> tuple[httpx.Request, BinaryIO | None]:
    headers = {
        "Authorization": f"Bearer {options.api_token}",
        "Accept": "application/json",
        "User-Agent": f"0bull-python/{__version__}",
    }
    data = {
        key: str(int(value)) if isinstance(value, bool) else str(value)
        for key, value in compact(rest.data).items()
    }
    files = dict(rest.files or {})
    opened: BinaryIO | None = None
    if rest.file is not None:
        field, source = rest.file
        name, content, content_type = to_file_content(source)
        files[field] = (name, content, content_type)
        if content is not source and isinstance(content, io.IOBase):
            opened = content
    # A file-free submission still requires multipart form encoding.
    multipart = (
        [(key, (None, value)) for key, value in data.items()] if rest.data is not None else []
    )
    request = httpx.Request(
        rest.method,
        f"{options.base_url}{rest.path}",
        headers=headers,
        params={
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in compact(rest.params).items()
        },
        json=(
            (compact(rest.json) if rest.compact_json else dict(rest.json))
            if rest.json is not None
            else None
        ),
        files=[*multipart, *files.items()] or None,
        extensions={"timeout": httpx.Timeout(options.timeout).as_dict()},
    )
    return request, opened


def _upload_request(options: ClientOptions, url: str, file: FileContent) -> httpx.Request:
    return httpx.Request(
        "POST",
        url,
        files={"video": file},
        headers={"Accept": "application/json", "User-Agent": f"0bull-python/{__version__}"},
        extensions={"timeout": httpx.Timeout(options.timeout).as_dict()},
    )


class SyncHTTPTransport:
    """Execute REST operations using an owned or injected httpx client."""

    supports_rest = True

    def __init__(self, options: ClientOptions, http_client: httpx.Client | None = None) -> None:
        self.options = options
        self._owns_client = http_client is None
        self._client = http_client if http_client is not None else httpx.Client()

    def _send(self, request: httpx.Request) -> httpx.Response:
        # Buffer the body up front so a 429 retry can replay it.
        request.read()
        attempts = 0
        while True:
            try:
                response = self._client.send(request, auth=None, follow_redirects=False)
            except httpx.TimeoutException as exc:
                raise APITimeoutError("API request timed out") from exc
            except httpx.TransportError as exc:
                raise APIConnectionError("API connection failed") from exc
            if response.status_code != 429 or attempts >= self.options.max_retries:
                return response
            attempts += 1
            time.sleep(_retry_after(response))

    def execute(self, operation: Operation[T]) -> T:
        """Send an operation and parse its successful response."""
        if operation.rest is None:
            name = operation.fun.fun if operation.fun else "Operation"
            raise NotImplementedError(f"{name} is not available over HTTP")
        request, opened = _request(self.options, operation.rest)
        try:
            response = self._send(request)
        finally:
            if opened is not None:
                opened.close()
        return operation.parse_rest(_check(response))

    def upload(self, url: str, file: FileContent) -> object:
        """POST a video to a signed URL without API authorization."""
        response = self._send(_upload_request(self.options, url, file))
        return _check(response).json()

    def close(self) -> None:
        """Close the underlying client only when created by this transport."""
        if self._owns_client:
            self._client.close()


class AsyncHTTPTransport:
    """Execute REST operations using an owned or injected httpx client."""

    supports_rest = True

    def __init__(
        self, options: ClientOptions, http_client: httpx.AsyncClient | None = None
    ) -> None:
        self.options = options
        self._owns_client = http_client is None
        self._client = http_client if http_client is not None else httpx.AsyncClient()

    async def _send(self, request: httpx.Request) -> httpx.Response:
        # Buffer the body up front so a 429 retry can replay it.
        request.read()
        attempts = 0
        while True:
            try:
                response = await self._client.send(request, auth=None, follow_redirects=False)
            except httpx.TimeoutException as exc:
                raise APITimeoutError("API request timed out") from exc
            except httpx.TransportError as exc:
                raise APIConnectionError("API connection failed") from exc
            if response.status_code != 429 or attempts >= self.options.max_retries:
                return response
            attempts += 1
            await asyncio.sleep(_retry_after(response))

    async def execute(self, operation: Operation[T]) -> T:
        """Send an operation and parse its successful response."""
        if operation.rest is None:
            name = operation.fun.fun if operation.fun else "Operation"
            raise NotImplementedError(f"{name} is not available over HTTP")
        request, opened = _request(self.options, operation.rest)
        try:
            response = await self._send(request)
        finally:
            if opened is not None:
                opened.close()
        return operation.parse_rest(_check(response))

    async def upload(self, url: str, file: FileContent) -> object:
        """POST a video to a signed URL without API authorization."""
        response = await self._send(_upload_request(self.options, url, file))
        return _check(response).json()

    async def aclose(self) -> None:
        """Close the underlying client only when created by this transport."""
        if self._owns_client:
            await self._client.aclose()
