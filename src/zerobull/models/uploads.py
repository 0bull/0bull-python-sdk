"""Uploads response models."""

from datetime import datetime

from ._base import ZeroBullModel

__all__ = ["UploadURL"]


class UploadURL(ZeroBullModel):
    """A signed URL for uploading a video."""

    upload_id: str
    upload_url: str
    expires_at: datetime
