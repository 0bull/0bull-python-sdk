"""Uploads operations."""

from ..models.uploads import UploadURL
from ._base import Operation, RestRequest, SocketFun, parse_model_socket, parse_model_unwrapped


def create() -> Operation[UploadURL]:
    """Mint a signed URL for uploading a video.

    The response is not wrapped in a data envelope on either transport.
    """
    return Operation(
        rest=RestRequest("POST", "/v1/uploads"),
        fun=SocketFun("/app/submissions/upload-url"),
        parse_rest=parse_model_unwrapped(UploadURL),
        parse_socket=parse_model_socket(UploadURL),
    )
