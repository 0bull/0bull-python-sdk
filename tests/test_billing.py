import pytest

from tests.conftest import MockAPI
from zerobull._operations import billing as billing_ops
from zerobull.models.billing import RentalItem

SUMMARY = {
    "subscribed": True,
    "phones": 3,
    "price_per_phone": 9.99,
    "monthly": 29.97,
    "on_grace_period": False,
    "pending_orders": [
        {
            "id": 1,
            "country": "US",
            "phones": 2,
            "availability": "now",
            "placed_at": "2026-01-01T00:00:00Z",
        }
    ],
    "lines": [
        {"id": 10, "status": "active", "cancelling": False, "renews_at": "2026-02-01T00:00:00Z"}
    ],
    "hint": "Renews soon",
}

SUMMARY_MINIMAL = {
    "subscribed": False,
    "phones": 0,
    "price_per_phone": 9.99,
    "pending_orders": [],
}

RENTAL = {
    "checkout_url": "https://checkout.stripe.com/abc",
    "phones": 5,
    "items": [{"country": "US", "quantity": 5}],
    "next": "poll GET /v1/billing",
}

CHANGE_APPLIED = {
    "applied": True,
    "request_id": "11111111-1111-1111-1111-111111111111",
    "from_phones": 3,
    "to_phones": 5,
    "next": "poll GET /v1/billing",
}

CHANGE_PENDING = {
    "applied": False,
    "request_id": "22222222-2222-2222-2222-222222222222",
    "approval_url": "https://0bull.net/approve/2",
    "from_phones": 3,
    "to_phones": 8,
    "charge_now": 10.0,
    "charge_on_assignment": None,
    "monthly_after": 79.92,
    "pricing_unavailable": False,
    "expires_at": "2026-01-02T00:00:00Z",
    "next": "poll GET /v1/billing/requests/2",
}

REQUEST_STATUS = {
    "request_id": "22222222-2222-2222-2222-222222222222",
    "status": "pending",
    "to_phones": 8,
    "approval_url": "https://0bull.net/approve/2",
    "expires_at": "2026-01-02T00:00:00Z",
    "resolved_at": None,
}


def test_summary(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/billing", json=SUMMARY)
    result = mock_api.client.billing.summary()
    assert result.subscribed is True and result.hint == "Renews soon"
    assert result.pending_orders[0].country == "US"
    assert result.lines[0].status == "active"
    request = mock_api.requests[-1]
    assert request.method == "GET" and request.url.path == "/api/v1/billing"

    op = billing_ops.summary()
    assert op.fun is not None
    assert op.fun.fun == "/app/billing/summary" and op.fun.data is None
    assert op.parse_socket is not None
    assert op.parse_socket(SUMMARY).hint == "Renews soon"


def test_summary_minimal_fields(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/billing", json=SUMMARY_MINIMAL)
    result = mock_api.client.billing.summary()
    assert result.monthly is None
    assert result.on_grace_period is None
    assert result.hint is None
    assert result.lines == []


@pytest.mark.anyio
async def test_async_summary(mock_api: MockAPI) -> None:
    mock_api.add("GET", "/api/v1/billing", json=SUMMARY)
    result = await mock_api.async_client.billing.summary()
    assert result.subscribed is True


def test_start_rental_with_phones(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/billing/rentals", json=RENTAL, status=201)
    result = mock_api.client.billing.start_rental(accept_terms=True, phones=5, country="US")
    assert result.checkout_url == RENTAL["checkout_url"]
    assert result.items[0].country == "US"
    record = mock_api.records[-1]
    assert record["method"] == "POST" and record["path"] == "/api/v1/billing/rentals"
    assert record["json"] == {"phones": 5, "country": "US", "accept_terms": True}

    op = billing_ops.start_rental(accept_terms=True, phones=5, country="US")
    assert op.fun is not None
    assert op.fun.fun == "/app/billing/rentals"
    assert op.fun.data == {"phones": 5, "country": "US", "items": None, "accept_terms": True}
    assert op.parse_socket is not None
    assert op.parse_socket(RENTAL).phones == 5


@pytest.mark.anyio
async def test_start_rental_with_items(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/billing/rentals", json=RENTAL, status=201)
    items: list[RentalItem | dict[str, object]] = [
        RentalItem(country="US", quantity=3),
        {"country": "CA", "quantity": 2},
    ]
    result = await mock_api.async_client.billing.start_rental(accept_terms=True, items=items)
    assert result.phones == RENTAL["phones"]
    record = mock_api.records[-1]
    assert record["json"] == {
        "items": [{"country": "US", "quantity": 3}, {"country": "CA", "quantity": 2}],
        "accept_terms": True,
    }


@pytest.mark.parametrize(
    "accept_terms,phones,country,items,match",
    [
        (False, 5, None, None, "accept_terms"),
        (True, None, None, None, "exactly one"),
        (True, 5, None, [{"country": "US", "quantity": 1}], "exactly one"),
        (True, 0, None, None, "phones"),
        (True, 51, None, None, "phones"),
        (True, 5, "us", None, "country"),
        (True, None, None, [], "items"),
        (True, None, None, [{"country": "US", "quantity": 1}] * 11, "items"),
        (True, None, None, [{"country": "US", "quantity": 0}], "quantity"),
    ],
)
def test_start_rental_validation(
    mock_api: MockAPI,
    accept_terms: bool,
    phones: int | None,
    country: str | None,
    items: list[dict[str, object]] | None,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        mock_api.client.billing.start_rental(
            accept_terms=accept_terms, phones=phones, country=country, items=items
        )
    assert mock_api.requests == []


def test_request_phone_count_applied(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/billing/requests", json=CHANGE_APPLIED, status=201)
    result = mock_api.client.billing.request_phone_count(accept_terms=True, phones=5)
    assert result.applied is True and result.to_phones == 5
    record = mock_api.records[-1]
    assert record["json"] == {"phones": 5, "accept_terms": True}


def test_request_phone_count_allows_zero_add(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/billing/requests", json=CHANGE_APPLIED, status=201)
    mock_api.client.billing.request_phone_count(accept_terms=True, add=0)
    record = mock_api.records[-1]
    assert record["json"] == {"add": 0, "accept_terms": True}


@pytest.mark.anyio
async def test_request_phone_count_pending(mock_api: MockAPI) -> None:
    mock_api.add("POST", "/api/v1/billing/requests", json=CHANGE_PENDING, status=202)
    result = await mock_api.async_client.billing.request_phone_count(accept_terms=True, add=5)
    assert result.applied is False and result.approval_url == CHANGE_PENDING["approval_url"]
    assert result.charge_on_assignment is None
    record = mock_api.records[-1]
    assert record["json"] == {"add": 5, "accept_terms": True}

    op = billing_ops.request_phone_count(accept_terms=True, add=5)
    assert op.fun is not None and op.fun.fun == "/app/billing/requests"
    assert op.fun.data == {"phones": None, "add": 5, "accept_terms": True}
    assert op.parse_socket is not None
    assert op.parse_socket(CHANGE_PENDING).request_id == CHANGE_PENDING["request_id"]


@pytest.mark.parametrize(
    "accept_terms,phones,add,match",
    [
        (False, 5, None, "accept_terms"),
        (True, None, None, "exactly one"),
        (True, 5, 1, "exactly one"),
        (True, 0, None, "phones"),
        (True, 51, None, "phones"),
        (True, None, 50, "add"),
        (True, None, -50, "add"),
    ],
)
def test_request_phone_count_validation(
    mock_api: MockAPI, accept_terms: bool, phones: int | None, add: int | None, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        mock_api.client.billing.request_phone_count(
            accept_terms=accept_terms, phones=phones, add=add
        )
    assert mock_api.requests == []


def test_get_request(mock_api: MockAPI) -> None:
    request_id = str(REQUEST_STATUS["request_id"])
    mock_api.add("GET", f"/api/v1/billing/requests/{request_id}", json=REQUEST_STATUS)
    result = mock_api.client.billing.get_request(request_id)
    assert result.status == "pending" and result.is_resolved is False
    request = mock_api.requests[-1]
    assert request.method == "GET" and request.url.path == f"/api/v1/billing/requests/{request_id}"

    op = billing_ops.get_request("abc")
    assert op.fun is not None
    assert op.fun.fun == "/app/billing/requests/get" and op.fun.data == {"request_id": "abc"}
    assert op.parse_socket is not None
    resolved = {**REQUEST_STATUS, "status": "approved"}
    assert op.parse_socket(resolved).is_resolved is True


@pytest.mark.anyio
async def test_async_get_request(mock_api: MockAPI) -> None:
    request_id = str(REQUEST_STATUS["request_id"])
    mock_api.add("GET", f"/api/v1/billing/requests/{request_id}", json=REQUEST_STATUS)
    result = await mock_api.async_client.billing.get_request(request_id)
    assert result.request_id == request_id
