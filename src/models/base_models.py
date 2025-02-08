from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field, PrivateAttr
from pydantic.alias_generators import to_camel


# TODO: this doesn't belong here - it's not a model
class Environment(str, Enum):
    """Supported application environments."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class SupabaseModel(BaseModel):
    """Base class for all models stored in the Supabase database."""

    _db_config: ClassVar[dict] = PrivateAttr(
        default={
            "schema": "",  # Database schema name
            "table": "",  # Table name
            "primary_key": "",  # Primary key field
        }
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last updated timestamp")

    def update(self, **kwargs: Any) -> Self:
        """Generic update method preserving model constraints."""
        protected = getattr(self, "_protected_fields", set())
        allowed_updates = {k: v for k, v in kwargs.items() if k not in protected}
        return self.model_copy(update=allowed_updates)


class APIModel(BaseModel):
    """Base class for all API data models.

    Enables:
    - Incoming JSON: to be converted from camelCase to snake_case
    - Outgoing JSON: to be converted from snake_case to camelCase
    """

    class Config:
        """Pydantic model configuration."""

        alias_generator = to_camel
        populate_by_name = True
