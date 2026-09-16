"""Submissions resources."""

from os import PathLike
from typing import BinaryIO

from .._operations import submissions
from .._pagination import AsyncPage, Page
from .._resource import AsyncResource, SyncResource
from .._transport._base import AsyncTransport, SyncTransport
from .._transport.http import AsyncHTTPTransport, SyncHTTPTransport
from .._wait import await_until, wait_until
from ..models.accounts import Platform
from ..models.submissions import Submission
from .uploads import AsyncUploads, Uploads


class Submissions(SyncResource):
    """Synchronous submissions resource."""

    def __init__(self, transport: SyncTransport, http: SyncHTTPTransport) -> None:
        super().__init__(transport, http)
        self._uploads = Uploads(transport, http)

    def list(
        self, *, page: int | None = None, platform: Platform | None = None
    ) -> Page[Submission]:
        """List video submissions, newest first."""
        data = self._execute(submissions.list(page=page, platform=platform))
        return Page(data, lambda next_page: self.list(page=next_page, platform=platform))

    def get(self, submission_id: int) -> Submission:
        """Get one submission by id."""
        return self._execute(submissions.get(submission_id))

    def create(
        self,
        *,
        account_id: str,
        platform: Platform | None = None,
        video: str | PathLike[str] | bytes | BinaryIO | None = None,
        video_url: str | None = None,
        upload_id: str | None = None,
        caption: str | None = None,
        draft: bool | None = None,
    ) -> Submission:
        """Create a submission from a local video, a URL, or a prior upload.

        A local video sent over the socket is uploaded through a signed URL
        first, since the socket cannot carry file bytes.

        Raises:
            ValueError: If not exactly one of video/video_url/upload_id is given,
                or the caption rules for the platform are not met.
        """
        if video is not None and (video_url is not None or upload_id is not None):
            raise ValueError("Exactly one of video, video_url, or upload_id is required")
        if video is not None and not self._transport.supports_rest:
            upload_id = self._uploads.upload(video)
            video = None
        return self._execute(
            submissions.create(
                account_id=account_id,
                platform=platform,
                video=video,
                video_url=video_url,
                upload_id=upload_id,
                caption=caption,
                draft=draft,
            )
        )

    def cancel(self, submission_id: int) -> Submission:
        """Cancel a queued or in-progress submission."""
        return self._execute(submissions.cancel(submission_id))

    def delete(self, submission_id: int) -> None:
        """Delete a submission and its stored video."""
        self._execute(submissions.delete(submission_id))

    def wait(
        self, submission: Submission | int, *, timeout: float = 900, interval: float = 5
    ) -> Submission:
        """Poll a submission until it reaches a terminal status.

        Raises:
            WaitTimeoutError: If the timeout elapses first.
        """
        submission_id = submission.id if isinstance(submission, Submission) else submission
        return wait_until(
            lambda: self.get(submission_id),
            lambda value: value.is_terminal,
            interval=interval,
            timeout=timeout,
            what=f"submission {submission_id}",
        )


class AsyncSubmissions(AsyncResource):
    """Asynchronous submissions resource."""

    def __init__(self, transport: AsyncTransport, http: AsyncHTTPTransport) -> None:
        super().__init__(transport, http)
        self._uploads = AsyncUploads(transport, http)

    async def list(
        self, *, page: int | None = None, platform: Platform | None = None
    ) -> AsyncPage[Submission]:
        """List video submissions, newest first."""
        data = await self._execute(submissions.list(page=page, platform=platform))

        async def fetch(next_page: int) -> AsyncPage[Submission]:
            return await self.list(page=next_page, platform=platform)

        return AsyncPage(data, fetch)

    async def get(self, submission_id: int) -> Submission:
        """Get one submission by id."""
        return await self._execute(submissions.get(submission_id))

    async def create(
        self,
        *,
        account_id: str,
        platform: Platform | None = None,
        video: str | PathLike[str] | bytes | BinaryIO | None = None,
        video_url: str | None = None,
        upload_id: str | None = None,
        caption: str | None = None,
        draft: bool | None = None,
    ) -> Submission:
        """Create a submission from a local video, a URL, or a prior upload.

        A local video sent over the socket is uploaded through a signed URL
        first, since the socket cannot carry file bytes.

        Raises:
            ValueError: If not exactly one of video/video_url/upload_id is given,
                or the caption rules for the platform are not met.
        """
        if video is not None and (video_url is not None or upload_id is not None):
            raise ValueError("Exactly one of video, video_url, or upload_id is required")
        if video is not None and not self._transport.supports_rest:
            upload_id = await self._uploads.upload(video)
            video = None
        return await self._execute(
            submissions.create(
                account_id=account_id,
                platform=platform,
                video=video,
                video_url=video_url,
                upload_id=upload_id,
                caption=caption,
                draft=draft,
            )
        )

    async def cancel(self, submission_id: int) -> Submission:
        """Cancel a queued or in-progress submission."""
        return await self._execute(submissions.cancel(submission_id))

    async def delete(self, submission_id: int) -> None:
        """Delete a submission and its stored video."""
        await self._execute(submissions.delete(submission_id))

    async def wait(
        self, submission: Submission | int, *, timeout: float = 900, interval: float = 5
    ) -> Submission:
        """Poll a submission until it reaches a terminal status.

        Raises:
            WaitTimeoutError: If the timeout elapses first.
        """
        submission_id = submission.id if isinstance(submission, Submission) else submission
        return await await_until(
            lambda: self.get(submission_id),
            lambda value: value.is_terminal,
            interval=interval,
            timeout=timeout,
            what=f"submission {submission_id}",
        )
