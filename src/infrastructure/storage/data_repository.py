from typing import Any, TypeVar
from uuid import UUID

from src.infrastructure.common.decorators import supabase_operation
from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.supabase_client import SupabaseClient
from src.models.base_models import SupabaseModel

logger = get_logger()
T = TypeVar("T", bound=SupabaseModel)  # define a generic type for the repository


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
        jobs = await repo.find(
            Job,
            filters={"status": JobStatus.PENDING}
        )

        # Complex JSONB queries
        sources = await repo.find(
            DataSource,
            filters={
                "metadata->url": "https://...",
                "status": SourceStatus.COMPLETED
            }
        )

        # Pagination and ordering
        requests = await repo.find(
            AddContentSourceRequest,
            order_by="created_at.desc",
            limit=10
        )
    """

    def __init__(self, db_client: SupabaseClient) -> None:
        self.db_client = db_client
        logger.debug("Initialized data repository")

    @supabase_operation
    async def save(self, entity: T | list[T]) -> T | list[T]:
        """Save or update an entity in the database.

        This method handles both insert and update operations through upsert.
        The operation is determined by the presence of the primary key value.

        Args:
            entity: Single entity or list of entities to save

        Returns:
            T | list[T]: Saved entity/entities with updated fields

        Examples:
            # Save new source
            source = DataSource(source_type=DataSourceType.WEB, ...)
            saved = await repo.save(source)

            # Update existing job
            job.status = JobStatus.COMPLETED
            updated = await repo.save(job)
        """
        client = await self.db_client.get_client()

        # Handle both single and batch cases
        entities = [entity] if not isinstance(entity, list) else entity
        if not entities:
            return []

        # All entities must be same type
        entity_type = type(entities[0])
        data = [e.model_dump(mode="json") for e in entities]

        # Single transaction for all entities
        result = await (
            client.schema(entity_type._db_config["schema"])
            .table(entity_type._db_config["table"])
            .upsert(data, on_conflict=entity_type._db_config["primary_key"])
            .execute()
        )

        # Return in same format as input
        saved = [entity_type.model_validate(item) for item in result.data]
        return saved if isinstance(entity, list) else saved[0]

    @supabase_operation
    async def find_by_id(self, model_class: type[T], id: UUID) -> T | None:
        """Retrieve a single entity by its primary key.

        Args:
            model_class: The model class to query
            id: Primary key value

        Returns:
            Entity instance or None if not found

        Examples:
            source = await repo.find_by_id(DataSource, source_id)
            job = await repo.find_by_id(Job, job_id)
        """
        result = await self.find(model_class=model_class, filters={model_class._db_config["primary_key"]: str(id)})
        if result:
            return model_class.model_validate(result[0])
        return None

    @supabase_operation
    async def find(
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
            jobs = await repo.find(
                Job,
                filters={"status": JobStatus.PENDING}
            )

            # Get sources with pagination
            sources = await repo.find(
                DataSource,
                filters={"status": SourceStatus.COMPLETED},
                order_by="created_at.desc",
                limit=10,
                offset=20
            )

            # Query by JSONB field
            requests = await repo.find(
                AddContentSourceRequest,
                filters={"request_config->url": "https://..."}
            )
        """
        client = await self.db_client.get_client()
        query = client.schema(model_class._db_config["schema"]).table(model_class._db_config["table"]).select("*")

        if filters:
            for field, value in filters.items():
                query = query.eq(field, value)

        if order_by:
            query = query.order(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        # Debugging: Log the query and filters
        logger.debug(f"Executing query with filters: {filters}")

        result = await query.execute()
        return [model_class.model_validate(item) for item in result.data]
