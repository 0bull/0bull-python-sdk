"""Billing operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..models.billing import BillingRequest, BillingSummary, PhoneCountChange, Rental, RentalItem
from ._base import (
    Operation,
    RestRequest,
    SocketFun,
    parse_model_socket,
    parse_model_unwrapped,
    path_segment,
    require_range,
)


def _require_accept_terms(accept_terms: bool) -> None:
    if not accept_terms:
        raise ValueError(
            "accept_terms must be True: show the user https://0bull.net/terms and "
            "https://0bull.net/privacy, including that this renews monthly, before charging"
        )


def _require_country(country: str | None) -> None:
    if country is not None and not (len(country) == 2 and country.isalpha() and country.isupper()):
        raise ValueError("country must be an ISO-3166 alpha-2 uppercase code")


def _item_dicts(items: Sequence[RentalItem | Mapping[str, object]]) -> list[dict[str, object]]:
    if not 1 <= len(items) <= 10:
        raise ValueError("items must have between 1 and 10 entries")
    dicts = [item.model_dump() if isinstance(item, RentalItem) else dict(item) for item in items]
    for item in dicts:
        quantity = item.get("quantity")
        if not isinstance(quantity, int) or not 1 <= quantity <= 50:
            raise ValueError("each item's quantity must be between 1 and 50")
    return dicts


def summary() -> Operation[BillingSummary]:
    """Get the account's billing summary."""
    return Operation(
        rest=RestRequest("GET", "/v1/billing"),
        fun=SocketFun("/app/billing/summary"),
        parse_rest=parse_model_unwrapped(BillingSummary),
        parse_socket=parse_model_socket(BillingSummary),
    )


def start_rental(
    *,
    accept_terms: bool,
    phones: int | None = None,
    country: str | None = None,
    items: Sequence[RentalItem | Mapping[str, object]] | None = None,
) -> Operation[Rental]:
    """Start a rental checkout for more phones.

    Returns a Stripe Checkout link; no phones are assigned until checkout
    completes and the order is fulfilled.
    """
    _require_accept_terms(accept_terms)
    _require_country(country)
    if (phones is None) == (items is None):
        raise ValueError("Pass exactly one of phones or items")
    if phones is not None:
        require_range("phones", phones, 1, 50)
    item_dicts = _item_dicts(items) if items is not None else None
    data = {"phones": phones, "country": country, "items": item_dicts, "accept_terms": accept_terms}
    return Operation(
        rest=RestRequest("POST", "/v1/billing/rentals", json=data),
        fun=SocketFun("/app/billing/rentals", data),
        parse_rest=parse_model_unwrapped(Rental),
        parse_socket=parse_model_socket(Rental),
    )


def request_phone_count(
    *, accept_terms: bool, phones: int | None = None, add: int | None = None
) -> Operation[PhoneCountChange]:
    """Request a change to the account's phone count.

    Applies immediately (201) if within the standing allowance, otherwise
    returns a pending approval request (202).
    """
    _require_accept_terms(accept_terms)
    if (phones is None) == (add is None):
        raise ValueError("Pass exactly one of phones or add")
    if phones is not None:
        require_range("phones", phones, 1, 50)
    if add is not None:
        require_range("add", add, -49, 49)
    data = {"phones": phones, "add": add, "accept_terms": accept_terms}
    return Operation(
        rest=RestRequest("POST", "/v1/billing/requests", json=data),
        fun=SocketFun("/app/billing/requests", data),
        parse_rest=parse_model_unwrapped(PhoneCountChange),
        parse_socket=parse_model_socket(PhoneCountChange),
    )


def get_request(request_id: str) -> Operation[BillingRequest]:
    """Get a billing request by id."""
    return Operation(
        rest=RestRequest("GET", f"/v1/billing/requests/{path_segment(request_id)}"),
        fun=SocketFun("/app/billing/requests/get", {"request_id": request_id}),
        parse_rest=parse_model_unwrapped(BillingRequest),
        parse_socket=parse_model_socket(BillingRequest),
    )
