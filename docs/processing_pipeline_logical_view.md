# Processing Pipeline Logical View

## 1. Component Responsibilities

### JobManager

- Does NOT get replaced by RQ. Instead, JobManager becomes the orchestrator that:
  1. Maintains the source of truth for job states in Supabase
  2. Provides job lifecycle management (create, update, complete, fail)
  3. Coordinates between your application state and RQ
  4. Exposes methods for job status queries and updates

Example implementation:

```python
class JobManager:
    def __init__(self, supabase_client: Client, redis_conn: Redis):
        self.supabase = supabase_client
        self.queue = Queue('processing', connection=redis_conn)

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

### Content Service

- Remains the entry point for content processing but delegates actual processing:
  1. Handles crawl completion webhook
  2. Creates processing jobs via JobManager
  3. Updates source status
  4. No direct processing logic

```python
class ContentService:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

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

### Processing Function

- The actual work that gets executed by RQ workers
- Pure processing logic, no job management
- Handles chunking and vector storage
- Reports progress and handles errors

```python
def process_documents(job_id: UUID, document_ids: list[UUID]):
    """This is the function that RQ workers execute"""
    try:
        # Initialize services
        job_manager = JobManager()
        chunker = Chunker()
        vector_db = VectorDB()

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

## 2. Data Flow

1. **Crawl Completion**

   - Webhook received by ContentService
   - Documents saved to database
   - Processing job created via JobManager
   - Source status updated to PROCESSING

2. **Job Creation**

   - JobManager creates job record in Supabase
   - JobManager enqueues processing work to RQ
   - RQ job ID stored with job record

3. **Processing Execution**

   - RQ worker picks up job from queue
   - Processing function executes
   - Progress updates sent to JobManager
   - Chunks stored in vector database

4. **Status Updates**
   - JobManager maintains job status in Supabase
   - RQ provides real-time job execution status
   - Status changes trigger source updates
   - Errors captured and stored with job

## 3. Error Handling and Recovery

1. **Job Level**

   - RQ handles worker crashes and job timeouts
   - Failed jobs can be retried automatically
   - Error details preserved in job record

2. **Document Level**

   - Processing errors for individual documents tracked
   - Partial completion possible
   - Failed documents logged for retry

3. **System Level**
   - Worker pool managed by RQ
   - Redis connection issues handled
   - Database transaction integrity maintained

## 4. Monitoring and Observability

1. **Job Metrics**

   - Processing time per document
   - Success/failure rates
   - Queue length and processing backlog
   - Worker utilization

2. **System Health**
   - RQ worker status
   - Redis connection status
   - Vector DB performance
   - Resource utilization
