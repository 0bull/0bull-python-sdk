"""Typed Python client for the 0bull API."""

from ._client import AsyncZeroBull, ZeroBull
from ._errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SocketClosedError,
    UnavailableError,
    ValidationError,
    WaitTimeoutError,
    ZeroBullError,
)
from ._pagination import AsyncPage, Page
from ._version import __version__

__all__ = [
    "APIConnectionError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncPage",
    "AsyncZeroBull",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "Page",
    "PermissionDeniedError",
    "RateLimitError",
    "SocketClosedError",
    "UnavailableError",
    "ValidationError",
    "WaitTimeoutError",
    "ZeroBull",
    "ZeroBullError",
    "__version__",
]
