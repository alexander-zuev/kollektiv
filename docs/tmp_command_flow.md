# Document Processing Implementation Plan

## 1. Project Structure Overview

kollektiv/
├── src/
│   ├── api/                    # API Layer
│   │   ├── v0/
│   │   │   ├── content/       # Content management endpoints
│   │   │   │   ├── document_router.py
│   │   │   │   └── crawl_router.py
│   │   │   └── chat/         # Chat endpoints
│   │   │       └── chat_router.py
│   │   ├── system/
│   │   │   ├── health/       # Health check endpoints
│   │   │   └── webhooks/     # Webhook handlers
│   │   └── middleware/       # API middleware
│   ├── models/               # Domain Models
│   │   ├── domain/          # Core business models
│   │   └── events/          # Event/webhook models
│   ├── interface/           # UI Layer
│   │   ├── flow_manager.py  # User input flow
│   │   ├── command_handler.py # Command processing
│   │   └── message_handler.py # Message routing
│   └── kollektiv/          # Core Business Logic
│       └── manager.py      # Main orchestrator

## 2. Core Domain Models

### 2.1 Document Models

# src/models/domain/document.py

class DocumentStatus(str, Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    CHUNKING = "chunking"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(BaseModel):
    id: str
    url: HttpUrl
    status: DocumentStatus
    created_at: datetime
    error: Optional[str]

### 2.2 Processing Models

# src/models/domain/processing.py

class ProcessingConfig(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=25, gt=0)
    exclude_patterns: list[str] = Field(default_factory=list)

## 3. Core Services

### 3.1 Document Service

# src/kollektiv/services/document.py

class DocumentService:
    """Handles document lifecycle and business logic"""

    def __init__(self, processor: DocumentProcessor):
        self.processor = processor

    async def add_document(self, config: ProcessingConfig) -> AsyncGenerator[Status, None]:
        # Document lifecycle management
        pass

### 3.2 Processing Pipeline

# src/kollektiv/services/processor.py

class DocumentProcessor:
    """Handles document processing pipeline"""

    def __init__(self, crawler: FireCrawler, chunker: MarkdownChunker, vector_db: VectorDB):
        self.crawler = crawler
        self.chunker = chunker
        self.vector_db = vector_db

## 4. API Layer

### 4.1 Public API (Document Management)

# src/api/v0/content/document_router.py

@router.post("/documents")
async def add_document(config: ProcessingConfig):
    """Start document processing pipeline"""
    return await document_service.add_document(config)

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get document status"""
    return await document_service.get_document(doc_id)

@router.get("/documents")
async def list_documents():
    """List all documents"""
    return await document_service.list_documents()

@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str):
    """Remove document"""
    return await document_service.remove_document(doc_id)

### 4.2 Internal Processing (Not Exposed)

# src/core/services/processor.py

class DocumentProcessor:
    """Internal processing pipeline"""
    def __init__(self, crawler: FireCrawler, ...):
        self.crawler = crawler
        ...

    async def process(self, document: Document) -> AsyncGenerator[Status, None]:
        # 1. Crawling (internal)
        crawl_result = await self.crawler.crawl(document.url)

        # 2. Processing
        chunks = await self.chunker.process(crawl_result)

        # 3. Storage
        await self.vector_db.store(chunks)

## 5. Implementation Plan

### Phase 1: Core Models & Services
1. Domain Models
   - [ ] Document model
   - [ ] Processing config
   - [ ] Status models
   - [ ] Event models

2. Core Services
   - [ ] Document service
   - [ ] Processing pipeline
   - [ ] Error handling

### Phase 2: Processing Pipeline
1. Crawler Integration
   - [ ] FireCrawl integration
   - [ ] Status tracking
   - [ ] Webhook handling

2. Content Processing
   - [ ] Chunking logic
   - [ ] Vector storage
   - [ ] Status updates

### Phase 3: API Implementation
1. Content Routes
   - [ ] Add document
   - [ ] Get status
   - [ ] List documents

2. System Routes
   - [ ] Health checks
   - [ ] Webhooks
   - [ ] Error handling

## 6. Error Handling

### 6.1 Custom Exceptions

# src/core/exceptions.py

class DocumentError(Exception):
    """Base exception for document operations"""
    pass

class ProcessingError(DocumentError):
    """Processing pipeline errors"""
    pass

### 6.2 Error Flow
1. Technical errors in processor
2. Business errors in service
3. API error responses
4. Status updates with errors

## 7. Testing Strategy

### 7.1 Unit Tests
- [ ] Domain model validation
- [ ] Service business logic
- [ ] API endpoint testing

### 7.2 Integration Tests
- [ ] End-to-end flows
- [ ] Webhook handling
- [ ] Error scenarios

## 8. Success Criteria

### 8.1 Functional Requirements
- [ ] Complete processing pipeline
- [ ] Error handling at all levels
- [ ] Status tracking and updates
- [ ] Document lifecycle management

### 8.2 Non-Functional Requirements
- [ ] API response times < 200ms
- [ ] Successful error recovery
- [ ] Clear status messages
- [ ] Comprehensive test coverage

## 9. Future Enhancements
1. Batch processing support
2. Content update mechanisms
3. Processing retry logic
4. Advanced status tracking
