from typing import Any, TypeVar
from uuid import UUID

from src.infrastructure.common.decorators import supabase_operation
from src.infrastructure.config.logger import get_logger
from src.infrastructure.external.supabase_client import SupabaseClient
from src.models.base_models import BaseDbModel

logger = get_logger()
T = TypeVar("T", bound=BaseDbModel)


class DataRepository:
    """Repository that handles all database operations.

    This repository provides a clean data access layer that:
    - Executes raw database operations (CRUD)
    - Handles database-specific implementation details
    - Maps database results to domain models
    - Isolates database-specific code from business logic

    Examples:
        # Save a source
        source = DataSource(source_type=DataSourceType.WEB, ...)
        saved = await repo.save(source)

        # Query jobs by status
        jobs = await repo.query(
            Job,
            filters={"status": JobStatus.PENDING}
        )

        # Complex JSONB queries
        sources = await repo.query(
            DataSource,
            filters={
                "metadata->url": "https://...",
                "status": SourceStatus.COMPLETED
            }
        )

        # Pagination and ordering
        requests = await repo.query(
            AddContentSourceRequest,
            order_by="created_at.desc",
            limit=10
        )
    """

    def __init__(self, db_client: SupabaseClient) -> None:
        self.db_client = db_client
        logger.debug("Initialized data repository")

    @supabase_operation
    async def save(self, entity: T) -> T:
        """Save or update an entity in the database.

        This method handles both insert and update operations through upsert.
        The operation is determined by the presence of the primary key value.

        Args:
            entity: Any model inheriting from BaseDbModel

        Returns:
            The saved entity with updated fields (e.g., created_at, updated_at)

        Examples:
            # Save new source
            source = DataSource(source_type=DataSourceType.WEB, ...)
            saved = await repo.save(source)

            # Update existing job
            job.status = JobStatus.COMPLETED
            updated = await repo.save(job)
        """
        client = await self.db_client.get_client()
        data = entity.model_dump(mode="json")

        logger.debug(f"Entity: {data}")

        result = await (
            client.schema(entity._db_config["schema"])
            .table(entity._db_config["table"])
            .upsert(data, on_conflict=entity._db_config["primary_key"])
            .execute()
        )

        return type(entity).model_validate(result.data[0])

    @supabase_operation
    async def get_by_id(self, model_class: type[T], id: UUID) -> T | None:
        """Retrieve an entity by its primary key.

        Args:
            model_class: The model class to query
            id: Primary key value

        Returns:
            Entity instance or None if not found

        Examples:
            source = await repo.get_by_id(DataSource, source_id)
            job = await repo.get_by_id(Job, job_id)
        """
        result = await self.query(model_class=model_class, filters={model_class._db_config["primary_key"]: str(id)})
        return result[0] if result else None

    @supabase_operation
    async def query(
        self,
        model_class: type[T],
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Execute a query with filters and pagination.

        Args:
            model_class: The model class to query
            filters: Field:value pairs supporting:
                - Simple equality: {"status": "pending"}
                - JSONB paths: {"metadata->url": "https://..."}
                - Nested JSONB: {"details->config->limit": 10}
            order_by: Field and direction (field.asc/desc)
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            List of model instances

        Examples:
            # Get pending jobs
            jobs = await repo.query(
                Job,
                filters={"status": JobStatus.PENDING}
            )

            # Get sources with pagination
            sources = await repo.query(
                DataSource,
                filters={"status": SourceStatus.COMPLETED},
                order_by="created_at.desc",
                limit=10,
                offset=20
            )

            # Query by JSONB field
            requests = await repo.query(
                AddContentSourceRequest,
                filters={"request_config->url": "https://..."}
            )
        """
        client = await self.db_client.get_client()
        query = client.schema(model_class._db_config["schema"]).table(model_class._db_config["table"]).select("*")

        if filters:
            for field, value in filters.items():
                if "->" in field:  # Handle JSONB queries
                    if isinstance(value, list):
                        query = query.contains(field, value)
                    else:
                        query = query.eq(field, str(value))
                else:
                    query = query.eq(field, value)

        if order_by:
            query = query.order(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        result = await query.execute()
        return [model_class.model_validate(item) for item in result.data]
