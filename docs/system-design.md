# Kollektiv System Design

## 1. Introduction & Requirements

### 1.1 Purpose
Kollektiv is a RAG-powered chat application enabling accurate, context-aware interactions with technical documentation through an AI interface.

### 1.2 Business Requirements

**Core Functionality**
- Process and index web-based documentation with high accuracy
- Enable natural language querying with context awareness
- Provide accurate, context-aware responses
- Support multiple document sources
- Real-time feedback and responses

**User Experience**
- Simple, intuitive interface
- Real-time responses
- Multi-document support

**Business Goals**
- Serve 10-1000 initial users
- Support self-hosted and SaaS deployments
- Enable future scaling

### 1.3 Quality Attributes
- Response Time: Sub-second for queries
- Accuracy: >90% relevant responses
- Availability: 99.9% uptime
- Data Freshness: Support manual reindexing

## 2. Architecture Overview

### 2.1 Design Principles

**Simplicity First**
- Single application deployment
- Minimal infrastructure complexity
- Clear service boundaries
Rationale: Reduces operational overhead, speeds development, easier maintenance

**Future-Proof Design**
- Modular services with clear interfaces
- Pluggable external services
- Domain-driven structure
Rationale: Enable component replacement and scaling without rewrites

**Resilient Processing**
- Comprehensive error tracking
- Automated recovery paths
- Status visibility
Rationale: Maintain reliability with minimal operational overhead

### 2.2 Technology Stack

**Core Stack**
- Python/FastAPI: Strong async support, excellent documentation
- Supabase: Handles auth and data with minimal overhead
- ChromaDB: Efficient vector storage, simple embedded mode
- Redis: Reliable job queue and real-time features

**AI/ML Stack**
- OpenAI: Text embeddings (text-embedding-3-small)
- Anthropic: Chat completion (Claude 3.5 Sonnet)
- Cohere: Result re-ranking

**Development Tools**
- Poetry: Dependency management
- Pytest: Testing framework
- Ruff: Code quality
- Chainlit: UI framework

## 3. Architecture Organization

### 3.1 Core Domains

1. **Content Management Domain**
   - Purpose: Handle document acquisition and processing
   - Key Concepts:
     - Documents, Chunks
     - Processing Jobs
     - Content Versions
   - Core Operations:
     - Document crawling
     - Content chunking
     - Version tracking

2. **Knowledge Engine Domain**
   - Purpose: Manage vector operations and search
   - Key Concepts:
     - Vector Embeddings
     - Search Queries
     - Ranking Results
   - Core Operations:
     - Embedding generation
     - Similarity search
     - Result ranking

3. **Chat Interface Domain**
   - Purpose: Handle user interactions and responses
   - Key Concepts:
     - Chat Sessions
     - Messages
     - Response Context
   - Core Operations:
     - Context management
     - Response generation
     - Stream handling

4. **System Core Domain**
   - Purpose: Manage cross-cutting concerns
   - Key Concepts:
     - Jobs
     - Events
     - Configuration
   - Core Operations:
     - Job orchestration
     - Event handling
     - Health monitoring

### 3.2 Domain Relationships

1. **Primary Flows**
   ```
   Content Management → Knowledge Engine
   - Document processing triggers embedding
   - Content updates require re-indexing

   Knowledge Engine → Chat Interface
   - Provides search results for queries
   - Manages context retrieval

   System Core ↔ All Domains
   - Coordinates operations
   - Manages state
   ```

2. **Event Flows**
   ```
   Content Events:
   Document Added → Processing → Indexed

   Chat Events:
   Query Received → Context Retrieved → Response Generated
   ```

### 3.3 Hybrid Package Structure

```
kollektiv/
├── src/
│   ├── api/                    # Interface Layer
│   │   ├── v0/                # API Version
│   │   │   ├── content/       # Content endpoints
│   │   │   │   ├── routes.py
│   │   │   │   └── schemas.py
│   │   │   ├── chat/         # Chat endpoints
│   │   │   └── system/       # System endpoints
│   │   └── middleware/       # API middleware
│   │
│   ├── core/               # Domain Logic
│   │   ├── content/         # Content Domain
│   │   │   ├── processing/  # Content processing
│   │   │   │   ├── chunker.py
│   │   │   │   └── crawler.py
│   │   │   └── repository.py
│   │   ├── knowledge/       # Knowledge Domain
│   │   │   ├── search.py
│   │   │   └── vectors.py
│   │   └── chat/           # Chat Domain
│   │       ├── session.py
│   │       └── generation.py
│   │
│   ├── models/              # Domain Models
│   │   ├── content/        # Content models
│   │   │   ├── document.py
│   │   │   └── chunk.py
│   │   ├── knowledge/      # Knowledge models
│   │   │   ├── embedding.py
│   │   │   └── search.py
│   │   └── chat/          # Chat models
│   │       ├── message.py
│   │       └── session.py
│   │
│   ├── services/           # Application Services
│   │   ├── content.py     # Content orchestration
│   │   ├── search.py      # Search orchestration
│   │   └── chat.py        # Chat orchestration
│   │
│   └── infrastructure/     # Technical Concerns
       ├── storage/        # Storage implementations
       │   ├── chroma.py
       │   └── redis.py
       ├── external/       # External services
       │   ├── firecrawl.py
       │   └── anthropic.py
       └── common/         # Shared utilities
           ├── config.py
           └── logging.py
```

### 3.4 Layer-Domain Mapping

1. **Interface Layer** (api/)
   - HTTP/WebSocket endpoints
   - Request/response handling
   - No domain logic

2. **Application Layer** (services/)
   - Orchestrates domain operations
   - Manages workflows
   - Uses domain models and logic

3. **Domain Layer** (domain/ + models/)
   - Core business logic
   - Domain models with behavior
   - Domain-specific operations

4. **Infrastructure Layer** (infrastructure/)
   - Technical implementations
   - External service integrations
   - Cross-cutting concerns

### 3.5 Implementation Guidelines

1. **Domain Models**
   - Rich models with behavior
   - Business rule enforcement
   - Domain event generation
   Example:
   ```python
   # models/content/document.py
   class Document:
       def __init__(self, url: str):
           self.url = url
           self._chunks = []
           self._state = DocumentState.NEW

       def chunk(self, strategy: ChunkingStrategy) -> None:
           """Apply chunking strategy and validate results."""
           if self._state != DocumentState.NEW:
               raise InvalidStateError("Document already chunked")

           self._chunks = strategy.chunk(self.content)
           self._state = DocumentState.CHUNKED
   ```

2. **Domain Services**
   - Complex operations
   - Multi-entity coordination
   Example:
   ```python
   # domain/content/processing/chunker.py
   class DocumentChunker:
       def process(self, doc: Document) -> list[Chunk]:
           """Process document with business rules."""
           strategy = self._select_strategy(doc)
           doc.chunk(strategy)
           return doc.chunks
   ```

3. **Application Services**
   - Workflow orchestration
   - Transaction management
   Example:
   ```python
   # services/content.py
   class ContentService:
       async def process_document(self, url: str) -> Document:
           """Orchestrate document processing workflow."""
           doc = await self.repository.create(url)
           chunks = await self.chunker.process(doc)
           await self.vector_service.embed(chunks)
           return doc
   ```

## 4. Development View

### 4.1 Layer Definitions

**Interface Layer**
- Primary: Handle external communication
- Components:
  - API Controllers: HTTP endpoints, validation
  - WebSocket Handlers: Real-time updates
  - Command Interface: Chainlit commands
- Design decisions:
  - Thin controllers
  - Consistent error handling
  - Clear API/UI separation

**Application Layer**
- Primary: Orchestrate domain operations
- Components:
  - Document Service: Processing pipeline
  - Chat Service: Conversation flow
  - Search Service: Retrieval/ranking
- Design decisions:
  - Service boundaries match domains
  - Stateless services
  - Clear external interfaces

**Domain Layer**
- Primary: Core business logic
- Components:
  - Domain Models: Business entities
  - Value Objects: Business rules
  - Domain Services: Complex operations
- Design decisions:
  - Rich domain models
  - Immutable value objects
  - Domain events

**Infrastructure Layer**
- Primary: Technical capabilities
- Components:
  - Repository Implementations
  - External Service Clients
  - Technical Services
- Design decisions:
  - Abstract dependencies
  - Consistent error handling
  - Configuration-driven

## 5. Process View

### 5.1 Runtime Components

**FastAPI Application**
- HTTP/WebSocket handling
- API routing
- Command processing
- UI integration

**Background Workers**
- Document processing
- Embedding generation
- Status updates
Implementation: Redis queue

**State Management**
- Job tracking
- Session management
- Processing status
Implementation: Redis with TTL

### 5.2 Key Processes

**Document Processing Pipeline**
States:
- PENDING: Initial request
- CRAWLING: FireCrawl active
- PROCESSING: Chunking/embedding
- COMPLETED: Indexed
- FAILED: Error state

Recovery:
- Automatic retries
- Manual intervention
- State restoration

**Query Processing Pipeline**
Steps:
- Query analysis/expansion
- Vector search
- Result re-ranking
- Response streaming

## 6. Package Structure

### 6.1 Organization Principles

1. **Hybrid Structure Rationale**
   - Separate technical layers (api, infrastructure)
   - Group domain logic by feature
   - Centralize models with domain alignment
   - Isolate cross-cutting concerns

2. **Key Design Decisions**
   - Models stay close to their domains
   - Business logic in domain services
   - Infrastructure concerns isolated
   - Clear dependency flow

### 6.2 Detailed Package Structure
```
kollektiv/
├── src/
│   ├── api/                    # Interface Layer
│   │   ├── v0/
│   │   │   ├── content/       # Content Management API
│   │   │   │   ├── routes.py  # HTTP endpoints
│   │   │   │   ├── schemas.py # Request/response models
│   │   │   │   └── deps.py    # Endpoint dependencies
│   │   │   ├── chat/          # Chat Interface API
│   │   │   │   ├── routes.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── stream.py  # SSE handling
│   │   │   └── system/        # System API
│   │   │       ├── health.py
│   │   │       └── webhooks.py
│   │   └── middleware/
│   │       ├── auth.py        # Authentication
│   │       ├── error.py       # Error handling
│   │       └── logging.py     # Request logging
│   │
│   ├── domain/                # Domain Logic
│   │   ├── content/
│   │   │   ├── processing/    # Content Processing
│   │   │   │   ├── chunker.py # Chunking logic
│   │   │   │   ├── crawler.py # Crawling logic
│   │   │   │   └── embedder.py # Embedding logic
│   │   │   └── repository.py  # Content persistence
│   │   ├── knowledge/
│   │   │   ├── engine.py     # Search coordination
│   │   │   ├── ranking.py    # Result ranking
│   │   │   └── vectors.py    # Vector operations
│   │   └── chat/
│   │       ├── session.py    # Session management
│   │       ├── context.py    # Context handling
│   │       └── generation.py # Response generation
│   │
│   ├── models/               # Domain Models
│   │   ├── base.py          # Base model classes
│   │   ├── mixins.py        # Shared behaviors
│   │   ├── content/
│   │   │   ├── document.py  # Document model
│   │   │   ├── chunk.py     # Chunk model
│   ���   │   └── job.py       # Processing job model
│   │   ├── knowledge/
│   │   │   ├── embedding.py # Embedding model
│   │   │   ├── query.py     # Query model
│   │   │   └── result.py    # Search result model
│   │   └── chat/
│   │       ├── message.py   # Message model
│   │       └── session.py   # Session model
│   │
│   ├── services/            # Application Services
│   │   ├── content.py      # Content workflows
│   │   ├── search.py       # Search workflows
│   │   └── chat.py         # Chat workflows
│   │
│   └── infrastructure/      # Infrastructure Layer
       ├── config/
       │   ├── settings.py   # Configuration
       │   └── logging.py    # Logging setup
       ├── storage/
       │   ├── chroma.py     # Vector store
       │   └── redis.py      # Cache/queue
       ├── external/
       │   ├── firecrawl.py  # Crawling API
       │   ├── anthropic.py  # LLM API
       │   └── cohere.py     # Ranking API
       └── common/
           ├── errors.py     # Error definitions
           └── utils.py      # Shared utilities
```

### 6.3 Implementation Guidelines

1. **Dependencies Flow**
```
api → services → domain → models
               ↘ infrastructure
```

2. **Key Files**
- `base.py`: Base classes and shared behaviors
- `routes.py`: API endpoint definitions
- `service.py`: Use case implementations
- `repository.py`: Data access patterns

3. **Cross-Cutting Concerns**
- Error handling in middleware
- Logging through infrastructure
- Configuration via settings

## 7. API Management

### 7.1 API Structure
```
/api/v0/
├── content/
│   ├── POST /crawl
│   ├── GET  /status
│   └── GET  /documents
├── chat/
│   ├── POST /message
│   └── GET  /stream
└── system/
    └── webhooks/
```

### 7.2 Webhook Handling
```
/webhooks/
├── firecrawl/  # Crawl updates
└── llm/        # LLM callbacks
```

## 8. Deployment Model

### 8.1 Application Architecture
- Single FastAPI application
- Embedded ChromaDB
- Redis for queues/real-time
- Supabase for auth/data

### 8.2 Infrastructure
```
Railway Project
├── FastAPI App
│   ├── API Server
│   ├── Workers
│   └── ChromaDB
└── Redis
    ├── Queue
    └── Pub/Sub
```

## 9. Technical Decisions & Rationale

### 9.1 Core Architecture Decisions

**Single Application Deployment**
Decision: Monolithic application with domain-based internal structure
Rationale:
- Current scale (1000 users) doesn't justify microservices overhead
- Faster development and simpler debugging
- Easier to refactor and extract services later
Trade-offs:
- Less scalability than microservices
- Tighter coupling between components
- Single point of failure
Migration Path:
- Extract ChromaDB when vector operations become bottleneck
- Split into services when domains need independent scaling
- Add API gateway when traffic patterns diversify

**State Management**
Decision: Redis for transient state, ChromaDB for vectors, Supabase for persistence
Rationale:
- Redis: Perfect for job queues and real-time updates
  - Built-in pub/sub for SSE
  - Atomic operations for job state
  - TTL for temporary data
- ChromaDB: Embedded mode for simplicity
  - Direct access to vector operations
  - No network overhead
  - Simple backup/restore
- Supabase: Managed service for auth/data
  - Reduces operational overhead
  - Built-in row-level security
  - PostgreSQL for complex queries

### 9.2 Domain-Specific Decisions

**Content Processing**
Decision: Async pipeline with status tracking
Implementation:
- FireCrawl for web crawling
  - Reliable HTML processing
  - Rate limiting handled
  - Webhook-based status updates
- Custom chunking strategies
  - Content-aware splitting
  - Metadata preservation
  - Configurable chunk sizes
- Embedding generation
  - Batched processing
  - Caching of embeddings
  - Version tracking

**Search & Retrieval**
Decision: Multi-stage search with re-ranking
Rationale:
- Better accuracy than single-stage search
- Manageable computational cost
- Easy to tune/modify components
Implementation:
- Query expansion for better recall
- Vector similarity for initial candidates
- Re-ranking for precision
- Response streaming for UX

### 9.3 Error Handling & Recovery

**Failure Domains**
- External Services
  - Retry with exponential backoff
  - Circuit breakers for protection
  - Fallback strategies defined
- Processing Pipeline
  - State recovery from crashes
  - Partial results handling
  - Manual intervention points
- User Interactions
  - Graceful degradation
  - Clear error messages
  - Recovery suggestions

**Error Propagation**
Decision: Domain-specific exceptions with global handling
Implementation:
- Custom exception hierarchy
- Error context preservation
- Structured logging
- User-friendly messages

### 9.4 Performance Strategy

**Response Time Targets**
- Chat responses: <1s for initial tokens
- Document processing: <5min for typical docs
- Search operations: <200ms for results

**Optimization Approach**
1. Measure First
   - Response time tracking
   - Resource utilization
   - Error rates
2. Optimize Hot Paths
   - Query caching
   - Connection pooling
   - Batch operations
3. Scale When Needed
   - Clear scaling triggers
   - Resource monitoring
   - Performance budgets

### 9.5 Security Model

**Authentication & Authorization**
Decision: Supabase Auth with custom RBAC
Rationale:
- Proven auth provider
- JWT-based sessions
- Built-in user management
Implementation:
- Role-based permissions
- Resource-level access control
- API rate limiting

**Data Protection**
- Encryption at rest for sensitive data
- TLS for all communications
- Regular security audits
- Clear data retention policies

## 10. Operations & Quality

### 10.1 Development Workflow
Decision: Trunk-based development with feature flags
Rationale:
- Rapid iteration needs
- Easy feature rollback
- Simple branching model

Implementation:
- Main branch always deployable
- Feature flags for new capabilities
- Automated testing gates
- Regular deployments

### 10.2 Quality Assurance

**Testing Strategy**
Decision: Focus on domain logic and RAG quality
Key Areas:
- Domain model behavior
- Processing pipeline reliability
- RAG response quality
- Integration points

**RAG Quality Metrics**
Primary:
- Answer relevance (>90%)
- Context accuracy (>95%)
- Response coherence
Implementation: Ragas-based evaluation suite

### 10.3 Monitoring & Recovery

**Critical Metrics**
- Processing pipeline health
  - Job completion rates
  - Processing times
  - Error patterns
- RAG performance
  - Query response times
  - Context relevance scores
  - User satisfaction metrics

**Recovery Procedures**
Priority order:
1. User-facing services (chat, search)
2. Processing pipeline
3. Background tasks

Automated recovery for:
- Failed crawl jobs
- Embedding generation
- Vector store operations

Manual intervention for:
- Data corruption
- Persistent external service failures
- Security incidents

## 11. Evolution Strategy

**Near-term Focus**
- RAG quality improvements
- Processing pipeline reliability
- User experience refinement

**Scale Triggers**
- Vector store separation: >100K documents
- Service extraction: >1000 concurrent users
- Load balancing: >100 req/s

**Migration Paths**
1. ChromaDB: Embedded → Dedicated
2. Processing: Sync → Async queue
3. Search: Single → Distributed

[End of document]
