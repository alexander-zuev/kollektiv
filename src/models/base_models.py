from datetime import UTC, datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field, PrivateAttr


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
