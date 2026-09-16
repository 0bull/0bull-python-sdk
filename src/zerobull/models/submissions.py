"""Submissions response models."""

from datetime import datetime
from typing import Literal

from ._base import ZeroBullModel

__all__ = [
    "TERMINAL_SUBMISSION_STATUSES",
    "Submission",
    "SubmissionFailure",
    "SubmissionStatus",
]

SubmissionStatus = Literal[
    "scheduled", "pending", "ingesting", "driving", "published", "drafted", "failed", "cancelled"
]

TERMINAL_SUBMISSION_STATUSES: frozenset[str] = frozenset(
    {"published", "drafted", "failed", "cancelled"}
)


class SubmissionFailure(ZeroBullModel):
    """Why a submission's publish attempt failed."""

    step: str | None
    message: str


class Submission(ZeroBullModel):
    """A queued or completed video submission."""

    id: int
    platform: str
    account_id: str | None
    caption: str | None
    draft: bool
    status: str
    attempts: int
    failure: SubmissionFailure | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    @property
    def is_terminal(self) -> bool:
        """Whether this submission has reached a terminal status."""
        return self.status in TERMINAL_SUBMISSION_STATUSES
