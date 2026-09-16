"""Typed WebSocket push events."""

from ._base import ZeroBullModel
from .billing import BillingRequest
from .runs import Run
from .submissions import Submission

__all__ = ["BillingRequestEvent", "Event", "RunEvent", "SubmissionEvent"]


class RunEvent(ZeroBullModel):
    """A phone run changed state."""

    run: Run


class SubmissionEvent(ZeroBullModel):
    """A video submission changed state."""

    submission: Submission


class BillingRequestEvent(ZeroBullModel):
    """A billing approval request changed state."""

    request: BillingRequest


Event = RunEvent | SubmissionEvent | BillingRequestEvent
