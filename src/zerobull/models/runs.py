"""Phone run responses and documented statuses."""

from datetime import datetime
from typing import Any, Literal

from ._base import ZeroBullModel

__all__ = ["TERMINAL_RUN_STATUSES", "Run", "RunKind", "RunStatus"]

RunKind = Literal["macro", "command", "agent"]
RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
TERMINAL_RUN_STATUSES: frozenset[str] = frozenset({"succeeded", "failed", "cancelled"})


class Run(ZeroBullModel):
    """A queued phone task and its eventual result."""

    id: str
    slot: str
    kind: str
    status: str
    label: str | None
    result: dict[str, Any] | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None

    @property
    def is_terminal(self) -> bool:
        """Whether the run has finished."""
        return self.status in TERMINAL_RUN_STATUSES

    @property
    def succeeded(self) -> bool:
        """Whether the run finished successfully."""
        return self.status == "succeeded"
