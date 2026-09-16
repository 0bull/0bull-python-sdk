"""Phone run history and polling resources."""

from .._operations import runs
from .._pagination import AsyncPage, Page
from .._resource import AsyncResource, SyncResource
from .._wait import await_until, wait_until
from ..models.runs import Run


class Runs(SyncResource):
    """Synchronous run access."""

    def list(self, slot: str, *, page: int | None = None) -> Page[Run]:
        """Get a page of phone runs; use iter_all() to traverse the history."""
        return Page(
            self._execute(runs.list(slot, page=page)), lambda number: self.list(slot, page=number)
        )

    def get(self, slot: str, run_id: str) -> Run:
        """Get the current status and result of a phone run."""
        return self._execute(runs.get(slot, run_id))

    def wait(self, run: Run, *, timeout: float = 300, interval: float = 2) -> Run:
        """Poll a run until terminal, raising WaitTimeoutError after timeout seconds."""
        return wait_until(
            lambda: self.get(run.slot, run.id),
            lambda value: value.is_terminal,
            timeout=timeout,
            interval=interval,
            what=f"run {run.id}",
        )


class AsyncRuns(AsyncResource):
    """Asynchronous run access."""

    async def list(self, slot: str, *, page: int | None = None) -> AsyncPage[Run]:
        """Get a page of phone runs; use iter_all() to traverse the history."""
        return AsyncPage(
            await self._execute(runs.list(slot, page=page)),
            lambda number: self.list(slot, page=number),
        )

    async def get(self, slot: str, run_id: str) -> Run:
        """Get the current status and result of a phone run."""
        return await self._execute(runs.get(slot, run_id))

    async def wait(self, run: Run, *, timeout: float = 300, interval: float = 2) -> Run:
        """Poll a run until terminal, raising WaitTimeoutError after timeout seconds."""
        return await await_until(
            lambda: self.get(run.slot, run.id),
            lambda value: value.is_terminal,
            timeout=timeout,
            interval=interval,
            what=f"run {run.id}",
        )
