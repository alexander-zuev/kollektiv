# Arq Migration

## Context
Celery does not natively support async operations.



## Problem Statement
Using Celery forces us to wrap async tasks inside synchronous functions (using `asyncio.run` etc.). This adds complexity, prevents genuine parallelism, and creates cumbersome orchestration (notably when using groups or chords for parallelism).

## Proposed Solution
Transition to [Arq](https://arq-docs.helpmanual.io/) because:
- Kollektiv is early-stage.
- Arq is actively maintained with native async support.
- It's built by the Pydantic founder
- Native async design simplifies orchestration and error handling.

## Worker Setup Checklist
1. **Redis Connection** ✅
   - Define `RedisSettings` for connecting to Redis since Arq uses Redis as its queue backend.
2. **Lifecycle Hooks** ✅
   - **on_startup**: Initialize worker services (e.g. create a singleton for `WorkerServices`).
   - **on_shutdown**: Shutdown or clean up any resources. ✅
3. **Worker Configuration** ✅
   - Create a main function that:
     - Establishes the Redis pool.
     - Provides the list of async task functions.
     - Optionally initializes a thread/process pool for blocking (sync) jobs.

## Key Migration Topics

### Local development
- Define changes necessary to compose.yaml
- Define changes to Dockerfile or settings

### Concurrency
- **How many workers?**
  Arq uses async workers—start with a small pool and scale based on resource utilization. Configure worker concurrency via command-line or settings.
- **Task parallelism:**
  Instead of Celery's `group`, simply enqueue jobs concurrently (or use `asyncio.gather` in a parent task if orchestration is needed).

### Startup & Shutdown
- **Worker Services:**
  Initialize worker services (from `worker_services.py`) in the `on_startup` coroutine.
- **Logging:**
  Set up logging in the on_startup hook so that each worker has its configuration upon boot.

### Idempotency
- **Pessimistic Execution:**
  ARQ may run jobs more than once if a worker shuts down abruptly.
- **Design Considerations:**
  Design jobs to be idempotent (use transactions, idempotency keys, or set Redis flags to mark completed API calls).

### Healthcheck
- ARQ updates a Redis key every `health_check_interval` seconds. Use this key to confirm that the worker is live.
- You can check health via the CLI:
  ```
  arq --check YourWorkerSettingsClass
  ```

### Serialization
- **Default Serializer:**
  ARQ uses MessagePack by default, which might differ slightly from your JSON-based Celery serialization.
- **Custom Handling:**
  Assess if additional serializer customization is needed for your Pydantic models. A helper for converting models to their dict (or JSON) representations may be useful.

### Task Queue Orchestration
- **Replacing `group`:**
  Enqueue multiple tasks concurrently. In an async context, use `await asyncio.gather(*tasks)` rather than a Celery group.
- **Replacing `chord`:**
  Instead of using a chord, chain tasks manually. For example, enqueue all subtasks and then enqueue a final "notification" task that polls or waits for completion.
- **Retry Policy:**
  Define retries within your task definitions or via your worker settings (e.g., using a `max_retries` parameter). ARQ supports retry parameters that can be set per job.

### Sync Jobs
- **Blocked Operations:**
  For CPU-bound tasks (like chunking), use an executor:
  ```python
  import asyncio
  from concurrent.futures import ProcessPoolExecutor

  async def run_sync_task(ctx, t):
      loop = asyncio.get_running_loop()
      return await loop.run_in_executor(ctx["pool"], sync_task, t)
  ```
  Initialize the executor in `on_startup` and shut it down in `on_shutdown`.

### Job Results & Enqueueing Tasks
- **Job Handling:**
  ARQ's `enqueue_job` returns a `Job` instance which can be used to query status and results.
- **From ContentService:**
  Instead of `celery_app.delay(...)`, use:
  ```python
  job = await redis.enqueue_job("your_task_name", arg1, arg2)
  ```
  This method allows you to chain or await completion if needed.

### Defining Tasks
Plan to define these tasks as async functions:
- `process_documents`
- `chunk_documents_batch`
- `persist_chunks`
- `check_chunking_complete`
- `generate_summary`
- `publish_event`



Each task should:
- Be written as an `async def` function.
- Use `await` instead of `asyncio.run`.
- Incorporate a retry mechanism via ARQ settings if necessary.

#### Simplified workflow
- `process_documents` -> accepts list of documents, user_id, source_id and fires up processing

It should:
- break down documents into batches (should be fast)
- schedule processing of these batches
- schedule check complition task with job ids
- it doesn't need to await the completion

- `chunk_documents_batch`
- accepts list of documents
- awaits processing of each batch
- schedules storage of all batches AND awaits results?

- `persist_chunks`
- accepts list of chunks
- sends them to vector db
- sends them to supabase

- `check_chunking_complete`
- accepts list of job ids
- awaits completion of all jobs
- if all jobs finished successfully -> generates a summary and schedules event publishing
- if some jobs failed -> schedules a notification to user with the error

- `generate_summary`
- accepts list of documents
- generates LLM summary
- schedules event publishing

- `publish_event`
- accepts event
- publishes it to the event bus

---

## Summary
- **Migrate to async-first tasks:** Rewrite tasks (from `tasks.py`) as async functions.
- **Use lifecycle hooks:** Replace Celery's process init logic (in `worker.py`) with ARQ's `on_startup` and `on_shutdown`.
- **Simplify orchestration:** Replace Celery chords/groups with async concurrency (`asyncio.gather`) or task chaining.
- **Plan for idempotency & retry:** Since ARQ may re-run jobs, ensure each job is designed to be safely repeatable.
- **Check serialization needs:** Decide if you need custom serialization beyond ARQ's default MessagePack.

This document should guide you to account for the differences between Celery and ARQ and help you design a cleaner, native async task queue.

Happy coding!
