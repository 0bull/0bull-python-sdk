import pytest

from zerobull import _errors as errors


@pytest.mark.parametrize(
    ("status", "name"),
    [
        (400, "BadRequestError"),
        (401, "AuthenticationError"),
        (403, "PermissionDeniedError"),
        (404, "NotFoundError"),
        (409, "ConflictError"),
        (422, "ValidationError"),
        (429, "RateLimitError"),
        (502, "UnavailableError"),
        (503, "UnavailableError"),
        (500, "InternalServerError"),
        (504, "InternalServerError"),
        (418, "APIStatusError"),
    ],
)
def test_status(status: int, name: str) -> None:
    error = errors.error_from_status(
        status, {"message": "bad", "errors": {"field": ["required"]}}, 2.5
    )
    assert type(error).__name__ == name
    assert error.status == status
    assert str(error) == error.message == "bad"
    assert error.errors == {"field": ["required"]}
    if isinstance(error, errors.RateLimitError):
        assert error.retry_after == 2.5


def test_fallback() -> None:
    assert errors.error_from_status(500, "oops").message == "oops"
    assert errors.error_from_status(500, None).message == "Server error"
    assert errors.error_from_status(504, None).message == "HTTP 504"
    assert errors.error_from_status(400, {"errors": "bad"}).errors == {}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, "Bad request"),
        (401, "Unauthenticated"),
        (403, "Forbidden"),
        (404, "Not found"),
        (409, "Conflict"),
        (422, "Validation failed"),
        (429, "Too many requests"),
        (500, "Server error"),
        (502, "Service unavailable"),
        (503, "Service unavailable"),
        (418, "HTTP 418"),
    ],
)
@pytest.mark.parametrize(
    "body",
    [
        {"message": ""},
        {"message": "   "},
        {},
    ],
)
def test_default_message_when_body_message_missing_or_blank(
    status: int, expected: str, body: dict[str, str]
) -> None:
    error = errors.error_from_status(status, body)
    assert error.message == expected
    assert str(error) == expected
    assert error.body == body
