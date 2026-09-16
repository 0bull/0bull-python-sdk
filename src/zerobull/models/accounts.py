"""Accounts response models."""

from datetime import datetime
from typing import Literal

from ._base import ZeroBullModel

__all__ = ["Account", "Platform"]

Platform = Literal["tiktok", "instagram", "youtube"]


class Account(ZeroBullModel):
    """A linked posting account."""

    id: str
    platform: str
    handle: str | None
    slot: str | None
    notes: str | None
    google_email: str | None = None
    created_at: datetime | None
    updated_at: datetime | None
