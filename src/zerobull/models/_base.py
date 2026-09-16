"""Common response model configuration."""

from pydantic import BaseModel, ConfigDict


class ZeroBullModel(BaseModel):
    """Immutable response model that preserves unknown fields."""

    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)
