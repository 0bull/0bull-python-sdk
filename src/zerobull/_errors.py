"""Shared REST and socket exceptions."""


class ZeroBullError(Exception):
    """Base exception for SDK failures."""


class APIStatusError(ZeroBullError):
    """An API error with its response status and field errors."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        errors: dict[str, list[str]] | None = None,
        body: object = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors or {}
        self.body = body


class BadRequestError(APIStatusError):
    """Malformed request."""


class AuthenticationError(APIStatusError):
    """Authentication failed."""


class PermissionDeniedError(APIStatusError):
    """Permission denied."""


class NotFoundError(APIStatusError):
    """Resource not found."""


class ConflictError(APIStatusError):
    """Resource state conflicts with the request."""


class ValidationError(APIStatusError):
    """Request validation failed."""


class UnavailableError(APIStatusError):
    """Service unavailable."""


class InternalServerError(APIStatusError):
    """Server failure."""


class APIConnectionError(ZeroBullError):
    """Network connection failed."""


class APITimeoutError(APIConnectionError):
    """Request or socket call timed out."""


class SocketClosedError(ZeroBullError):
    """Socket closed while a call was in flight."""


class WaitTimeoutError(ZeroBullError):
    """Polling deadline expired."""


class RateLimitError(APIStatusError):
    """Rate limit exceeded after retries."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        errors: dict[str, list[str]] | None = None,
        body: object = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status=status, errors=errors, body=body)
        self.retry_after = retry_after


_DEFAULT_MESSAGES = {
    400: "Bad request",
    401: "Unauthenticated",
    403: "Forbidden",
    404: "Not found",
    409: "Conflict",
    422: "Validation failed",
    429: "Too many requests",
    500: "Server error",
    502: "Service unavailable",
    503: "Service unavailable",
}


def error_from_status(
    status: int, body: object, retry_after: float | None = None
) -> APIStatusError:
    """Map an API response to the shared exception hierarchy."""
    message = _DEFAULT_MESSAGES.get(status, f"HTTP {status}")
    errors: dict[str, list[str]] = {}
    if isinstance(body, dict):
        raw_message = body.get("message")
        if isinstance(raw_message, str) and raw_message.strip():
            message = raw_message
        fields = body.get("errors")
        if isinstance(fields, dict):
            errors = {
                key: value
                for key, value in fields.items()
                if isinstance(key, str)
                and isinstance(value, list)
                and all(isinstance(item, str) for item in value)
            }
    elif isinstance(body, str) and body.strip():
        message = body
    if status == 429:
        return RateLimitError(
            message, status=status, errors=errors, body=body, retry_after=retry_after
        )
    cls = {
        400: BadRequestError,
        401: AuthenticationError,
        403: PermissionDeniedError,
        404: NotFoundError,
        409: ConflictError,
        422: ValidationError,
        502: UnavailableError,
        503: UnavailableError,
    }.get(status, InternalServerError if status >= 500 else APIStatusError)
    return cls(message, status=status, errors=errors, body=body)
