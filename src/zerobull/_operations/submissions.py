"""Submissions operations."""

from os import PathLike
from typing import BinaryIO

from .._pagination import PageData
from ..models.accounts import Platform
from ..models.submissions import Submission
from ._base import (
    Operation,
    RestRequest,
    SocketFun,
    no_content,
    parse_model,
    parse_model_socket,
    parse_page,
    parse_page_socket,
    to_file_content,
)


def _check_caption(caption: str | None, platform: Platform | None) -> None:
    if (platform or "tiktok") == "youtube":
        if not caption:
            raise ValueError("caption is required for youtube submissions")
        limit = 100
    else:
        limit = 2200
    if caption is not None and len(caption) > limit:
        raise ValueError(f"caption must be at most {limit} characters")


def list(
    *, page: int | None = None, platform: Platform | None = None
) -> Operation[PageData[Submission]]:
    """List the authenticated user's video submissions."""
    return Operation(
        rest=RestRequest("GET", "/v1/submissions", params={"page": page, "platform": platform}),
        fun=SocketFun("/app/submissions/list", {"page": page, "platform": platform}),
        parse_rest=parse_page(Submission),
        parse_socket=parse_page_socket(Submission),
    )


def get(submission_id: int) -> Operation[Submission]:
    """Get one submission by id."""
    return Operation(
        rest=RestRequest("GET", f"/v1/submissions/{submission_id}"),
        fun=SocketFun("/app/submissions/get", {"submission": submission_id}),
        parse_rest=parse_model(Submission),
        parse_socket=parse_model_socket(Submission),
    )


def create(
    *,
    account_id: str,
    platform: Platform | None = None,
    video: str | PathLike[str] | bytes | BinaryIO | None = None,
    video_url: str | None = None,
    upload_id: str | None = None,
    caption: str | None = None,
    draft: bool | None = None,
) -> Operation[Submission]:
    """Create a submission from a local video, a URL, or a prior upload.

    A local video cannot be sent over the socket, so the returned operation
    has no socket fun in that case; the resource uploads it over HTTP first.

    Raises:
        ValueError: If not exactly one of video/video_url/upload_id is given,
            or the caption rules for the platform are not met.
    """
    sources = [source for source in (video, video_url, upload_id) if source is not None]
    if len(sources) != 1:
        raise ValueError("Exactly one of video, video_url, or upload_id is required")
    _check_caption(caption, platform)
    files = None
    if video is not None:
        name, content, content_type = to_file_content(video)
        files = {"video": (name, content, content_type)}
    return Operation(
        rest=RestRequest(
            "POST",
            "/v1/submissions",
            data={
                "platform": platform,
                "account_id": account_id,
                "video_url": video_url,
                "upload_id": upload_id,
                "caption": caption,
                "draft": draft,
            },
            files=files,
        ),
        fun=None
        if video is not None
        else SocketFun(
            "/app/submissions/create",
            {
                "platform": platform,
                "account": account_id,
                "video_url": video_url,
                "upload_id": upload_id,
                "caption": caption,
                "draft": draft,
            },
        ),
        parse_rest=parse_model(Submission),
        parse_socket=parse_model_socket(Submission),
    )


def cancel(submission_id: int) -> Operation[Submission]:
    """Cancel a queued or in-progress submission."""
    return Operation(
        rest=RestRequest("POST", f"/v1/submissions/{submission_id}/cancel"),
        fun=SocketFun("/app/submissions/cancel", {"submission": submission_id}),
        parse_rest=parse_model(Submission),
        parse_socket=parse_model_socket(Submission),
    )


def delete(submission_id: int) -> Operation[None]:
    """Delete a submission and its stored video."""
    return Operation(
        rest=RestRequest("DELETE", f"/v1/submissions/{submission_id}"),
        fun=SocketFun("/app/submissions/delete", {"submission": submission_id}),
        parse_rest=no_content,
        parse_socket=no_content,
    )
