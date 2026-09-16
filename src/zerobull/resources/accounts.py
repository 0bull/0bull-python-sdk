"""Accounts resources."""

from .._operations import accounts
from .._operations._base import NOT_GIVEN, NotGivenOr
from .._pagination import AsyncPage, Page
from .._resource import AsyncResource, SyncResource
from ..models.accounts import Account, Platform


class Accounts(SyncResource):
    """Synchronous accounts resource."""

    def list(self, *, page: int | None = None, platform: Platform | None = None) -> Page[Account]:
        """List posting accounts, newest first."""
        data = self._execute(accounts.list(page=page, platform=platform))
        return Page(data, lambda next_page: self.list(page=next_page, platform=platform))

    def get(self, account_id: str) -> Account:
        """Get one account by id."""
        return self._execute(accounts.get(account_id))

    def create(
        self,
        *,
        handle: str,
        platform: Platform | None = None,
        slot: str | None = None,
        notes: str | None = None,
        google_email: str | None = None,
    ) -> Account:
        """Link a new posting account.

        Raises:
            ValueError: If google_email or slot is missing or invalid for the platform.
        """
        return self._execute(
            accounts.create(
                handle=handle,
                platform=platform,
                slot=slot,
                notes=notes,
                google_email=google_email,
            )
        )

    def update(
        self,
        account_id: str,
        *,
        handle: NotGivenOr[str] = NOT_GIVEN,
        slot: NotGivenOr[str | None] = NOT_GIVEN,
        notes: NotGivenOr[str | None] = NOT_GIVEN,
        google_email: NotGivenOr[str | None] = NOT_GIVEN,
    ) -> Account:
        """Update only the fields passed; omitted fields are unchanged.

        Raises:
            ValueError: If no field is passed.
        """
        return self._execute(
            accounts.update(
                account_id, handle=handle, slot=slot, notes=notes, google_email=google_email
            )
        )

    def delete(self, account_id: str) -> None:
        """Delete an account."""
        self._execute(accounts.delete(account_id))


class AsyncAccounts(AsyncResource):
    """Asynchronous accounts resource."""

    async def list(
        self, *, page: int | None = None, platform: Platform | None = None
    ) -> AsyncPage[Account]:
        """List posting accounts, newest first."""
        data = await self._execute(accounts.list(page=page, platform=platform))
        return AsyncPage(data, lambda next_page: self.list(page=next_page, platform=platform))

    async def get(self, account_id: str) -> Account:
        """Get one account by id."""
        return await self._execute(accounts.get(account_id))

    async def create(
        self,
        *,
        handle: str,
        platform: Platform | None = None,
        slot: str | None = None,
        notes: str | None = None,
        google_email: str | None = None,
    ) -> Account:
        """Link a new posting account.

        Raises:
            ValueError: If google_email or slot is missing or invalid for the platform.
        """
        return await self._execute(
            accounts.create(
                handle=handle,
                platform=platform,
                slot=slot,
                notes=notes,
                google_email=google_email,
            )
        )

    async def update(
        self,
        account_id: str,
        *,
        handle: NotGivenOr[str] = NOT_GIVEN,
        slot: NotGivenOr[str | None] = NOT_GIVEN,
        notes: NotGivenOr[str | None] = NOT_GIVEN,
        google_email: NotGivenOr[str | None] = NOT_GIVEN,
    ) -> Account:
        """Update only the fields passed; omitted fields are unchanged.

        Raises:
            ValueError: If no field is passed.
        """
        return await self._execute(
            accounts.update(
                account_id, handle=handle, slot=slot, notes=notes, google_email=google_email
            )
        )

    async def delete(self, account_id: str) -> None:
        """Delete an account."""
        await self._execute(accounts.delete(account_id))
