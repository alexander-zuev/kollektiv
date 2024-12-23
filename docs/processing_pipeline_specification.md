# Processing Pipeline Specification

## 1. Current State Analysis

### Architecture

- Content Service creates CRAWL jobs and handles crawl completion
- Job Manager supports basic CRUD operations
- Chunker has robust chunking logic but needs integration
- Vector DB handles document storage but needs batch processing
- Currently blocking operations in Content Service

### Pain Points

- Content Service is tightly coupled with processing logic
- No background processing mechanism
- Blocking operations affect API responsiveness
- No clear separation between crawling and processing phases
- Job data is not persisted reliably

## 2. Target State: Logical View

### Component Responsibilities

#### JobManager

- Does NOT get replaced by RQ. Instead, JobManager becomes the orchestrator that:

  1.  Maintains the source of truth for job states in Supabase
  2.  Provides job lifecycle management (create, update, complete, fail)
  3.  Coordinates between your application state and RQ
  4.  Exposes methods for job status queries and updates

  Example implementation:

  ```python
  from rq import Queue
  from redis import Redis
  from src.models.job_models import Job, JobStatus, JobType
  from src.infrastructure.external.supabase_client import supabase_client
  from src.services.data_service import DataService
  from uuid import UUID

  class JobManager:
      def __init__(self, data_service: DataService, redis_client: Redis):
          self.data_service = data_service
          self.queue = Queue('processing', connection=redis_client)

      async def create_processing_job(self, source_id: UUID, document_ids: list[UUID]) -> Job:
          # 1. Create job record in Supabase
          job = await self._create_job_record(
              job_type=JobType.PROCESS,
              source_id=source_id,
              details={"document_ids": document_ids}
          )

          # 2. Enqueue actual processing work to RQ
          rq_job = self.queue.enqueue(
              'process_documents',
              args=[job.job_id, document_ids],
              job_timeout='1h'
          )

          # 3. Update job with RQ job ID
          await self._update_job(job.job_id, {"rq_job_id": rq_job.id})

          return job

      async def get_job_status(self, job_id: UUID) -> JobStatus:
          # Get status from both Supabase and RQ
          job = await self._get_job(job_id)
          if job.rq_job_id:
              rq_job = self.queue.fetch_job(job.rq_job_id)
              # Sync RQ status with our job status if needed
              if self._needs_status_sync(job, rq_job):
                  await self._sync_job_status(job, rq_job)
          return job.status
  ```

#### Content Service

- Remains the entry point for content processing but delegates actual processing:

  1.  Handles crawl completion webhook
  2.  Creates processing jobs via JobManager
  3.  Updates source status
  4.  No direct processing logic

  ```python
  from src.models.job_models import Job, JobStatus, JobType
  from src.models.content_models import SourceStatus
  from uuid import UUID

  class ContentService:
      def __init__(self, job_manager: JobManager, data_service: DataService, crawler):
          self.job_manager = job_manager
          self.data_service = data_service
          self.crawler = crawler

      async def _handle_crawl_completed(self, job: Job) -> None:
          # Save documents from crawl
          documents = await self.crawler.get_results(job.details["firecrawl_id"])
          saved_docs = await self.data_service.save_documents(documents)

          # Create processing job
          processing_job = await self.job_manager.create_processing_job(
              source_id=job.source_id,
              document_ids=[doc.id for doc in saved_docs]
          )

          # Update source status
          await self.data_service.update_datasource(
              source_id=job.source_id,
              updates={
                  "status": SourceStatus.PROCESSING,
                  "job_id": processing_job.job_id
              }
          )
  ```

#### Processing Function

- The actual work that gets executed by RQ workers
- Pure processing logic, no job management
- Handles chunking and vector storage
- Reports progress and handles errors

  ```python
  from src.services.job_manager import JobManager
  from src.core.content.chunker import Chunker
  from src.core.search.vector_db import VectorDB
  from src.services.data_service import DataService
  from src.models.job_models import JobStatus
  from uuid import UUID

  def process_documents(job_id: UUID, document_ids: list[UUID]):
      """This is the function that RQ workers execute"""
      try:
          # Initialize services
          job_manager = JobManager()
          chunker = Chunker()
          vector_db = VectorDB()
          data_service = DataService()

          # Update job status
          job_manager.update_job(job_id, status=JobStatus.IN_PROGRESS)

          # Process each document
          for doc_id in document_ids:
              # Get document
              document = data_service.get_document(doc_id)

              # Generate chunks
              chunks = chunker.process_document(document)

              # Store in vector DB
              vector_db.add_documents(chunks)

              # Update progress
              job_manager.update_job_progress(job_id, processed_doc_id=doc_id)

          # Mark job as complete
          job_manager.complete_job(job_id)

      except Exception as e:
          # Handle failure
          job_manager.fail_job(job_id, error=str(e))
          raise
  ```

### Data Flow

1.  **Crawl Completion**

    - Webhook received by ContentService
    - Documents saved to database
    - Processing job created via JobManager
    - Source status updated to PROCESSING

2.  **Job Creation**

    - JobManager creates job record in Supabase
    - JobManager enqueues processing work to RQ
    - RQ job ID stored with job record

3.  **Processing Execution**

    - RQ worker picks up job from queue
    - Processing function executes
    - Progress updates sent to JobManager
    - Chunks stored in vector database

4.  **Status Updates**
    - JobManager maintains job status in Supabase
    - RQ provides real-time job execution status
    - Status changes trigger source updates
    - Errors captured and stored with job

### Error Handling and Recovery

1.  **Job Level**

    - RQ handles worker crashes and job timeouts
    - Failed jobs can be retried automatically
    - Error details preserved in job record

2.  **Document Level**

    - Processing errors for individual documents tracked
    - Partial completion possible
    - Failed documents logged for retry

3.  **System Level**
    - Worker pool managed by RQ
    - Redis connection issues handled
    - Database transaction integrity maintained

### Monitoring and Observability

1.  **Job Metrics**

    - Processing time per document
    - Success/failure rates
    - Queue length and processing backlog
    - Worker utilization

2.  **System Health**
    - RQ worker status
    - Redis connection status
    - Vector DB performance
    - Resource utilization

## 3. Data Models

### Job Models

    ```python
    class JobStatus(str, Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class JobType(str, Enum):
        CRAWL = "crawl"
        PROCESS = "process"

    class ProcessingJobDetails(BaseModel):
        """Details for processing jobs"""
        source_id: UUID
        document_ids: list[UUID]
        chunk_count: int = 0
        processed_count: int = 0
        error_count: int = 0
    ```

### Processing Worker Configuration

    ```python
    class ProcessingConfig(BaseModel):
        """Configuration for the processing worker"""
        poll_interval: int = 30  # seconds
        batch_size: int = 100
        max_retries: int = 3
        backoff_factor: float = 1.5
        max_concurrent_jobs: int = 5
    ```

## 4. Implementation Plan

### Phase 1: Basic Processing Pipeline

1. Create ProcessingWorker class
2. Implement job polling mechanism
3. Add basic error handling and retries
4. Integrate with existing Chunker

### Phase 2: Redis Integration

1. Set up Redis for job queue
2. Modify JobManager to use Redis
3. Update ProcessingWorker to use Redis queue
4. Add job result storage

### Phase 3: Performance Optimization

1. Implement batch processing
2. Add concurrent job processing
3. Optimize vector storage operations
4. Add monitoring and metrics

## 5. Redis Integration Details

### Queue Structure

    ```python
    # Redis key patterns
    JOB_QUEUE = "processing:queue"
    JOB_STATUS = "processing:status:{job_id}"
    JOB_RESULT = "processing:result:{job_id}"
    ```

### Job Flow

1. Content Service creates job and adds to Redis queue
2. ProcessingWorker polls queue for new jobs
3. Job status updates stored in Redis
4. Results stored in Redis with TTL

## 6. Error Handling

### Retry Strategy

- Exponential backoff for retries
- Maximum retry attempts configurable
- Failed jobs marked with error details

### Error Types

1. **Transient Errors**

   - Network issues
   - Rate limits
   - Temporary service unavailability

2. **Permanent Errors**
   - Invalid content
   - Missing documents
   - Configuration errors
