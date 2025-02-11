# Content Ingestion Feature

## SSE Workflow

SourceEvents are emitted at the following stages:
CREATED -> published after initial data source entry created
CRAWLING_STARTED -> published after first crawl_started event
PROCESSING_SCHEDULED -> published after processing task is scheduled
SUMMARY_GENERATED -> publshed after summary is generated
COMPLETED -> published after processing is complete
FAILED -> published if any step of content ingestion process fails

### Mapping of ContentProcessingEvents to SourceEvents
STARTED -> internal event, is not sent to FE
CHUNKS_GENERATED -> internal event, is not sent to FE
SUMMARY_GENERATED -> sent to FE
COMPLETED -> sent to FE
FAILED -> sent to FE


## API Endpoints

## Data Model
