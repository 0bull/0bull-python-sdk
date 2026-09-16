"""Client configuration resolved from arguments and environment."""

import os
from dataclasses import dataclass, field

from ._errors import ZeroBullError


@dataclass(frozen=True)
class ClientOptions:
    """Resolved connection settings; token is excluded from repr."""

    api_token: str | None = field(default=None, repr=False)
    base_url: str | None = None
    timeout: float = 30.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        token = self.api_token if self.api_token is not None else os.getenv("ZEROBULL_API_TOKEN")
        if not token:
            raise ZeroBullError(
                "An API token is required: pass api_token or set ZEROBULL_API_TOKEN"
            )
        base = (
            self.base_url
            if self.base_url is not None
            else os.getenv("ZEROBULL_BASE_URL", "https://0bull.net/api")
        )
        object.__setattr__(self, "api_token", token)
        object.__setattr__(self, "base_url", base.rstrip("/"))
