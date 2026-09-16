"""Uploads resources."""

import io
from os import PathLike
from typing import BinaryIO

from .._operations import uploads
from .._operations._base import to_file_content
from .._resource import AsyncResource, SyncResource
from ..models.uploads import UploadURL


class Uploads(SyncResource):
    """Synchronous uploads resource."""

    def create(self) -> UploadURL:
        """Mint a signed URL for uploading a video."""
        return self._execute(uploads.create())

    def upload(self, video: str | PathLike[str] | bytes | BinaryIO) -> str:
        """Upload a local video through a freshly minted signed URL.

        Returns:
            The upload id, to pass as submissions.create(upload_id=...).
        """
        url = self.create()
        name, content, content_type = to_file_content(video)
        try:
            self._http.upload(url.upload_url, (name, content, content_type))
        finally:
            if content is not video and isinstance(content, io.IOBase):
                content.close()
        return url.upload_id


class AsyncUploads(AsyncResource):
    """Asynchronous uploads resource."""

    async def create(self) -> UploadURL:
        """Mint a signed URL for uploading a video."""
        return await self._execute(uploads.create())

    async def upload(self, video: str | PathLike[str] | bytes | BinaryIO) -> str:
        """Upload a local video through a freshly minted signed URL.

        Returns:
            The upload id, to pass as submissions.create(upload_id=...).
        """
        url = await self.create()
        name, content, content_type = to_file_content(video)
        try:
            await self._http.upload(url.upload_url, (name, content, content_type))
        finally:
            if content is not video and isinstance(content, io.IOBase):
                content.close()
        return url.upload_id
