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
from ._socket import AsyncSocket, Socket
from ._version import __version__
from .models.events import BillingRequestEvent, Event, RunEvent, SubmissionEvent

__all__ = [
    "APIConnectionError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncPage",
    "AsyncSocket",
    "AsyncZeroBull",
    "AuthenticationError",
    "BadRequestError",
    "BillingRequestEvent",
    "ConflictError",
    "Event",
    "InternalServerError",
    "NotFoundError",
    "Page",
    "PermissionDeniedError",
    "RateLimitError",
    "RunEvent",
    "Socket",
    "SocketClosedError",
    "SubmissionEvent",
    "UnavailableError",
    "ValidationError",
    "WaitTimeoutError",
    "ZeroBull",
    "ZeroBullError",
    "__version__",
]
