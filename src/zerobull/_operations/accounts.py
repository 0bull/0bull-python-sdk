"""Accounts operations."""

from .._pagination import PageData
from ..models.accounts import Account, Platform
from ._base import (
    NOT_GIVEN,
    NotGivenOr,
    Operation,
    RestRequest,
    SocketFun,
    compact_given,
    no_content,
    parse_model,
    parse_model_socket,
    parse_page,
    parse_page_socket,
    path_segment,
)


def list(
    *, page: int | None = None, platform: Platform | None = None
) -> Operation[PageData[Account]]:
    """List the authenticated user's posting accounts."""
    return Operation(
        rest=RestRequest("GET", "/v1/accounts", params={"page": page, "platform": platform}),
        fun=SocketFun("/app/accounts/list", {"page": page, "platform": platform}),
        parse_rest=parse_page(Account),
        parse_socket=parse_page_socket(Account),
    )


def get(account_id: str) -> Operation[Account]:
    """Get one account by id."""
    return Operation(
        rest=RestRequest("GET", f"/v1/accounts/{path_segment(account_id)}"),
        fun=SocketFun("/app/accounts/get", {"account": account_id}),
        parse_rest=parse_model(Account),
        parse_socket=parse_model_socket(Account),
    )


def create(
    *,
    handle: str,
    platform: Platform | None = None,
    slot: str | None = None,
    notes: str | None = None,
    google_email: str | None = None,
) -> Operation[Account]:
    """Link a new posting account.

    Raises:
        ValueError: If google_email or slot is missing or invalid for the platform.
    """
    effective_platform = platform or "tiktok"
    if google_email is not None and effective_platform != "youtube":
        raise ValueError("google_email is only valid for youtube accounts")
    if effective_platform == "youtube" and google_email is None:
        raise ValueError("google_email is required for youtube accounts")
    if effective_platform == "tiktok" and slot is None:
        raise ValueError("slot is required for tiktok accounts")
    payload = {
        "platform": platform,
        "handle": handle,
        "slot": slot,
        "notes": notes,
        "google_email": google_email,
    }
    return Operation(
        rest=RestRequest("POST", "/v1/accounts", json=payload),
        fun=SocketFun("/app/accounts/create", payload),
        parse_rest=parse_model(Account),
        parse_socket=parse_model_socket(Account),
    )


def update(
    account_id: str,
    *,
    handle: NotGivenOr[str] = NOT_GIVEN,
    slot: NotGivenOr[str | None] = NOT_GIVEN,
    notes: NotGivenOr[str | None] = NOT_GIVEN,
    google_email: NotGivenOr[str | None] = NOT_GIVEN,
) -> Operation[Account]:
    """Update only the fields the caller passes.

    Raises:
        ValueError: If no field is passed.
    """
    fields = compact_given(
        {"handle": handle, "slot": slot, "notes": notes, "google_email": google_email}
    )
    if not fields:
        raise ValueError("At least one field is required to update an account")
    return Operation(
        rest=RestRequest(
            "PUT", f"/v1/accounts/{path_segment(account_id)}", json=fields, compact_json=False
        ),
        fun=SocketFun("/app/accounts/update", {"account": account_id, **fields}, compact=False),
        parse_rest=parse_model(Account),
        parse_socket=parse_model_socket(Account),
    )


def delete(account_id: str) -> Operation[None]:
    """Delete an account."""
    return Operation(
        rest=RestRequest("DELETE", f"/v1/accounts/{path_segment(account_id)}"),
        fun=SocketFun("/app/accounts/delete", {"account": account_id}),
        parse_rest=no_content,
        parse_socket=no_content,
    )
