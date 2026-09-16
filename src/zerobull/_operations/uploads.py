"""Uploads operations."""

from ..models.uploads import UploadURL
from ._base import Operation, RestRequest, SocketFun, parse_model_socket


def create() -> Operation[UploadURL]:
    """Mint a signed URL for uploading a video.

    The response is not wrapped in a data envelope on either transport.
    """
    return Operation(
        rest=RestRequest("POST", "/v1/uploads"),
        fun=SocketFun("/app/submissions/upload-url"),
        parse_rest=lambda response: UploadURL.model_validate(response.json()),
        parse_socket=parse_model_socket(UploadURL),
    )
