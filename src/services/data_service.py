from typing import Any, TypeVar
from uuid import UUID

from src.api.v0.schemas.sources_schemas import AddContentSourceRequest
from src.core._exceptions import (
    DatabaseError,
    EntityNotFoundError,
    EntityValidationError,
)
from src.infrastructure.common.logger import get_logger
from src.infrastructure.storage.data_repository import DataRepository
from src.models.base_models import BaseDbModel
from src.models.content_models import DataSource, Document, SourceSummary
from src.models.job_models import Job

logger = get_logger()

T = TypeVar("T", bound=BaseDbModel)


class DataService:
    """Service layer responsible for coordinating data operations and business logic.

    This service acts as an intermediary between the application and data access layer.
    It handles:
    - Business logic and validation
    - Data transformation and mapping
    - Coordination between multiple repositories if needed
    - Transaction management
    - Event emission for data changes

    The service uses DataRepository for actual database operations while focusing on
    higher-level business operations and data integrity.
    """

    def __init__(self, repository: DataRepository):
        self.repository = repository
        logger.debug("Initialized data service")

    # Core methods used by all services

    async def save_entity(self, entity: T) -> T:
        """Save entity with proper error handling."""
        try:
            logger.debug(f"Saving {type(entity).__name__}")
            result = await self.repository.save(entity)
            return type(entity).model_validate(result)
        except DatabaseError as e:
            raise e.add_context(operation="save_entity", entity_type=type(entity).__name__) from e
        except ValueError as e:
            # Convert the error message to a dictionary format
            error_details = {"error": str(e)}
            raise EntityValidationError(type(entity).__name__, error_details) from e

    async def get_entity(self, model_class: type[T], entity_id: UUID) -> T:
        """Generic get by ID operation.

        Args:
            model_class: The model class to query
            entity_id: Primary key value

        Returns:
            Entity instance

        Raises:
            EntityNotFoundError: If entity not found
            DatabaseError: If database operation fails
        """
        logger.debug(f"Getting {model_class.__name__} with ID {entity_id}")
        try:
            result = await self.repository.get_by_id(model_class, entity_id)
            if not result:
                logger.error(f"{model_class.__name__} {entity_id} not found")
                raise EntityNotFoundError(f"{model_class.__name__} {entity_id} not found")

            # Ensure type safety through validation
            entity = model_class.model_validate(result)
            return entity

        except DatabaseError:
            raise  # Re-raise DatabaseError

    async def query_entities(
        self,
        model_class: type[T],
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Generic query operation with pagination support."""
        logger.debug(f"Querying {model_class.__name__} with filters: {filters}")
        try:
            results = await self.repository.query(
                model_class=model_class, filters=filters, order_by=order_by, limit=limit, offset=offset
            )
            return [model_class.model_validate(result) for result in results]
        except DatabaseError as e:
            logger.error(f"Database error querying entities: {e}")
            raise  # Re-raise DatabaseError

    async def update_entity(self, model_class: type[T], entity_id: UUID, updates: dict[str, Any]) -> T:
        """Generic update operation for any entity."""
        # Get and validate current entity
        current = await self.get_entity(model_class, entity_id)

        # Create updated copy with validation
        updated = model_class.model_validate(current.model_dump())
        updated = updated.model_copy(update=updates)

        # Save and validate result
        result = await self.save_entity(updated)
        return model_class.model_validate(result.model_dump())

    # Convenience methods with proper type safety

    async def save_job(self, job: Job) -> Job:
        """Save or update a job."""
        logger.debug(f"Saving job {job.job_id}")
        result = await self.save_entity(job)
        # Explicit type cast to satisfy mypy
        return Job.model_validate(result.model_dump())

    async def get_job(self, job_id: UUID) -> Job:
        """Get job by ID with proper type casting."""
        result = await self.get_entity(Job, job_id)
        # Explicit type cast to satisfy mypy
        return Job.model_validate(result.model_dump())

    async def get_by_firecrawl_id(self, firecrawl_id: str) -> Job | None:
        """Get job by FireCrawl ID with proper type casting."""
        jobs = await self.query_entities(Job, filters={"details->>firecrawl_id": firecrawl_id})
        if not jobs:
            return None
        return Job.model_validate(jobs[0].model_dump())

    async def save_datasource(self, data_source: DataSource) -> DataSource:
        """Save or update a data source."""
        logger.debug(f"Saving data source {data_source.source_id}")
        result = await self.save_entity(data_source)
        return DataSource.model_validate(result)

    async def update_datasource(self, source_id: UUID, updates: dict[str, Any]) -> DataSource:
        """Update a data source with new data."""
        result = await self.update_entity(DataSource, source_id, updates)
        return DataSource.model_validate(result)

    async def save_user_request(self, request: AddContentSourceRequest) -> AddContentSourceRequest:
        """Save user request."""
        logger.debug(f"Saving user request {request.request_id}")
        result = await self.save_entity(request)
        return AddContentSourceRequest.model_validate(result)

    async def save_documents(self, documents: list[Document]) -> list[Document]:
        """Saves list of crawled documents."""
        logger.debug(f"Saving list of documents {len(documents)}")
        saved_documents = await self.repository.save(entity=documents)

        return [Document.model_validate(document) for document in saved_documents]

    async def list_datasources(self) -> list[DataSource]:
        """List all data sources."""
        results = await self.query_entities(DataSource)
        # Ensure each result is properly validated and type-cast
        return [DataSource.model_validate(result.model_dump()) for result in results]

    async def retrieve_datasource(self, source_id: UUID) -> DataSource:
        """Get data source by ID."""
        result = await self.get_entity(DataSource, source_id)
        return DataSource.model_validate(result)

    async def _load_summaries(self) -> list[SourceSummary]:
        """Load document summaries from Supabase storage."""
        pass

    async def save_summaries(self, summaries: list[SourceSummary]) -> list[SourceSummary]:
        """Save document summaries to Supabase storage."""
        pass

    async def get_all_summaries(self) -> list[SourceSummary]:
        """Get all document summaries."""
        pass

    async def clear_summaries(self) -> None:
        """Clear all document summaries."""
        pass

    async def get_documents_by_source(self, source_id: UUID) -> list[Document]:
        """Get documents by source ID."""
        documents = await self.query_entities(Document, filters={"source_id": source_id})
        return [Document.model_validate(document) for document in documents]

    async def update_document_status(self, document_id: UUID, error: str | None = None) -> None:
        """Update document status."""
        await self.update_entity(Document, document_id, {"error": error})
