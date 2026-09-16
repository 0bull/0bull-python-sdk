"""Billing resources."""

from collections.abc import Mapping, Sequence

from .._operations import billing
from .._resource import AsyncResource, SyncResource
from ..models.billing import BillingRequest, BillingSummary, PhoneCountChange, Rental, RentalItem


class Billing(SyncResource):
    """Synchronous billing resource."""

    def summary(self) -> BillingSummary:
        """Get the account's billing summary."""
        return self._execute(billing.summary())

    def start_rental(
        self,
        *,
        accept_terms: bool,
        phones: int | None = None,
        country: str | None = None,
        items: Sequence[RentalItem | Mapping[str, object]] | None = None,
    ) -> Rental:
        """Start a rental checkout for more phones."""
        return self._execute(
            billing.start_rental(
                accept_terms=accept_terms, phones=phones, country=country, items=items
            )
        )

    def request_phone_count(
        self, *, accept_terms: bool, phones: int | None = None, add: int | None = None
    ) -> PhoneCountChange:
        """Request a change to the account's phone count."""
        return self._execute(
            billing.request_phone_count(accept_terms=accept_terms, phones=phones, add=add)
        )

    def get_request(self, request_id: str) -> BillingRequest:
        """Get a billing request by id."""
        return self._execute(billing.get_request(request_id))


class AsyncBilling(AsyncResource):
    """Asynchronous billing resource."""

    async def summary(self) -> BillingSummary:
        """Get the account's billing summary."""
        return await self._execute(billing.summary())

    async def start_rental(
        self,
        *,
        accept_terms: bool,
        phones: int | None = None,
        country: str | None = None,
        items: Sequence[RentalItem | Mapping[str, object]] | None = None,
    ) -> Rental:
        """Start a rental checkout for more phones."""
        return await self._execute(
            billing.start_rental(
                accept_terms=accept_terms, phones=phones, country=country, items=items
            )
        )

    async def request_phone_count(
        self, *, accept_terms: bool, phones: int | None = None, add: int | None = None
    ) -> PhoneCountChange:
        """Request a change to the account's phone count."""
        return await self._execute(
            billing.request_phone_count(accept_terms=accept_terms, phones=phones, add=add)
        )

    async def get_request(self, request_id: str) -> BillingRequest:
        """Get a billing request by id."""
        return await self._execute(billing.get_request(request_id))
