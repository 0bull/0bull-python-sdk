"""Transport-independent operation definitions and response parsers."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Generic, Literal, TypeVar, cast

from pydantic import BaseModel, TypeAdapter

from .._pagination import PageData

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
FileContent = bytes | BinaryIO | tuple[str, bytes | BinaryIO, str]


@dataclass(frozen=True)
class RestResponse:
    """Raw REST response passed to an operation parser."""

    status: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> object:
        """Decode JSON, returning None for an empty body."""
        return json.loads(self.content) if self.content else None


@dataclass(frozen=True)
class RestRequest:
    """REST method, relative path and optional payloads."""

    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str
    params: Mapping[str, object] | None = None
    json: Mapping[str, object] | None = None
    data: Mapping[str, object] | None = None
    files: Mapping[str, FileContent] | None = None


@dataclass(frozen=True)
class SocketFun:
    """Socket function and unwrapped request data."""

    fun: str
    data: Mapping[str, object] | None = None


@dataclass(frozen=True)
class Operation(Generic[T]):
    """One operation with mappings and parsers for both transports."""

    rest: RestRequest | None
    fun: SocketFun | None
    parse_rest: Callable[[RestResponse], T]
    parse_socket: Callable[[object], T] | None = None


def compact(mapping: Mapping[str, object] | None) -> dict[str, object]:
    """Drop top-level None values without altering nested payloads."""
    return {key: value for key, value in (mapping or {}).items() if value is not None}


def unwrap(response: RestResponse) -> object:
    """Extract a REST data envelope."""
    body = response.json()
    if not isinstance(body, dict) or "data" not in body:
        raise ValueError("Expected a response with a data field")
    return body["data"]


def parse_model(model_cls: type[M]) -> Callable[[RestResponse], M]:
    """Build a parser for a wrapped REST model."""
    return lambda response: model_cls.model_validate(unwrap(response))


def parse_model_socket(model_cls: type[M]) -> Callable[[object], M]:
    """Build a parser for an unwrapped socket model."""
    return model_cls.model_validate


def parse_page_socket(model_cls: type[M]) -> Callable[[object], PageData[M]]:
    """Validate page items and metadata from a socket data object."""

    def parse(body: object) -> PageData[M]:
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise ValueError("Expected page data and meta")
        meta = TypeAdapter(dict[str, int]).validate_python(body.get("meta"))
        return PageData(
            [model_cls.model_validate(item) for item in body["data"]],
            meta["current_page"],
            meta["last_page"],
            meta["per_page"],
            meta["total"],
        )

    return parse


def parse_page(model_cls: type[M]) -> Callable[[RestResponse], PageData[M]]:
    """Build a parser for a REST page, ignoring extra metadata."""
    socket_parser = parse_page_socket(model_cls)

    def parse(response: RestResponse) -> PageData[M]:
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("meta"), dict):
            raise ValueError("Expected page data and meta")
        return socket_parser(
            {
                "data": body.get("data"),
                "meta": {
                    key: body["meta"][key]
                    for key in ("current_page", "last_page", "per_page", "total")
                },
            }
        )

    return parse


def no_content(response: object) -> None:
    """Ignore the body of an operation with no result."""


def require_range(name: str, value: float | None, low: float, high: float) -> None:
    """Reject a supplied value outside the documented inclusive range."""
    if value is not None and not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")


def to_file_content(
    video: str | os.PathLike[str] | bytes | BinaryIO,
) -> tuple[str, BinaryIO | bytes, str]:
    """Prepare a video; caller owns any stream opened from a path."""
    if isinstance(video, (str, os.PathLike)):
        path = Path(video)
        name, content = path.name, cast("BinaryIO | bytes", path.open("rb"))
    elif isinstance(video, bytes):
        name, content = "video", video
    else:
        name, content = Path(str(getattr(video, "name", "video"))).name, video
    content_type = {".mp4": "video/mp4", ".mov": "video/quicktime"}.get(
        Path(name).suffix.lower(), "application/octet-stream"
    )
    return name, content, content_type
