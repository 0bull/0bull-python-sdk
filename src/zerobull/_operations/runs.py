"""Phone run lookup operations."""

from .._pagination import PageData
from ..models.runs import Run
from ._base import (
    Operation,
    RestRequest,
    SocketFun,
    compact,
    parse_model,
    parse_model_socket,
    parse_page,
    parse_page_socket,
    path_segment,
)


def list(slot: str, *, page: int | None = None) -> Operation[PageData[Run]]:
    """List the run history for a phone, with optional one-based page."""
    if page is not None and page < 1:
        raise ValueError("page must be at least 1")
    return Operation(
        rest=RestRequest(
            "GET", f"/v1/phones/{path_segment(slot)}/runs", params=compact({"page": page})
        ),
        fun=SocketFun("/app/phones/runs", compact({"slot": slot, "page": page})),
        parse_rest=parse_page(Run),
        parse_socket=parse_page_socket(Run),
    )


def get(slot: str, run_id: str) -> Operation[Run]:
    """Get one run belonging to a phone."""
    return Operation(
        rest=RestRequest("GET", f"/v1/phones/{path_segment(slot)}/runs/{path_segment(run_id)}"),
        fun=SocketFun("/app/phones/runs/get", {"slot": slot, "run": run_id}),
        parse_rest=parse_model(Run),
        parse_socket=parse_model_socket(Run),
    )
