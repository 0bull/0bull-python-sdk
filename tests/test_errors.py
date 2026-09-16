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
    assert errors.error_from_status(500, None).message == "HTTP 500"
    assert errors.error_from_status(400, {"errors": "bad"}).errors == {}
