"""Billing response models."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from ._base import ZeroBullModel

__all__ = [
    "BillingLine",
    "BillingRequest",
    "BillingRequestStatus",
    "BillingSummary",
    "PendingOrder",
    "PhoneCountChange",
    "Rental",
    "RentalItem",
]

BillingRequestStatus = Literal["pending", "approved", "declined", "failed", "expired"]


class PendingOrder(ZeroBullModel):
    """A rental order awaiting fulfillment."""

    id: int
    country: str
    phones: int
    availability: str
    placed_at: datetime


class BillingLine(ZeroBullModel):
    """A Stripe subscription line on the account."""

    id: int
    status: str
    cancelling: bool
    renews_at: datetime | None


class BillingSummary(ZeroBullModel):
    """Active rentals, pending orders, pricing and renewal dates."""

    subscribed: bool
    phones: int
    price_per_phone: float
    monthly: float | None = None
    on_grace_period: bool | None = None
    pending_orders: list[PendingOrder]
    lines: list[BillingLine] = Field(default_factory=list)
    hint: str | None = None


class RentalItem(ZeroBullModel):
    """A country and phone quantity within a rental."""

    country: str
    quantity: int


class Rental(ZeroBullModel):
    """A Stripe Checkout link for a rental order."""

    checkout_url: str
    phones: int
    items: list[RentalItem]
    next: str


class PhoneCountChange(ZeroBullModel):
    """The result of requesting a phone count change, applied or pending."""

    applied: bool
    request_id: str
    from_phones: int
    to_phones: int
    next: str
    approval_url: str | None = None
    charge_now: float | None = None
    charge_on_assignment: float | None = None
    monthly_after: float | None = None
    pricing_unavailable: bool | None = None
    expires_at: datetime | None = None


class BillingRequest(ZeroBullModel):
    """A billing request's approval status."""

    request_id: str
    status: str
    to_phones: int
    approval_url: str
    expires_at: datetime
    resolved_at: datetime | None

    @property
    def is_resolved(self) -> bool:
        """Whether the request has left the pending state."""
        return self.status != "pending"
