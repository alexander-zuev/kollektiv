1. Introduction
1.1 Purpose
Kollektiv is a RAG-powered chat application enabling users to interact with their documentation through an AI interface.

1.2 Business Requirements
Core Functionality

Process and index web-based documentation

Enable natural language querying

Provide accurate, context-aware responses

User Experience

Simple, intuitive interface

Real-time responses

Multi-document support

Business Goals

Serve 10-1000 initial users

Support self-hosted and SaaS deployments

Enable future scaling

2. Architecture Overview
2.1 Design Principles
Simplicity First

Single application deployment

Minimal infrastructure complexity

Clear service boundaries
Rationale: Reduces operational overhead, speeds development, easier maintenance

Future-Proof Design

Modular services

Clear interfaces

Scalable patterns
Rationale: Enables future growth without major refactoring

2.2 Technology Choices
Core Stack

Python/FastAPI
Rationale: Strong async support, excellent documentation, great ecosystem

Supabase
Rationale: Handles auth and data with minimal overhead

ChromaDB
Rationale: Efficient vector storage, simple embedded mode

Redis
Rationale: Reliable job queue and real-time features

3. Development & Operations
3.1 Local Development
Environment Setup

Poetry for dependency management

Local Redis instance
Rationale: Development independence from production

Local ChromaDB persistence

Supabase CLI for local auth

4. Core Services
Content Service

Document ingestion & processing

Chunking & versioning

Content management

Vector Service

Embedding generation

Vector storage & search

Result ranking

Chat Service

Session management

LLM integration

Response streaming

User Service

Authentication via Supabase

User management

Usage tracking

5. Core Data Flows
Content Processing Flow
Frontend submits URL

Content Service validates & initiates crawl

Background worker processes content

Vector Service indexes content

Status updates via SSE to frontend
Rationale: Asynchronous processing for better user experience

Chat Interaction Flow
User sends message

Chat Service processes query

Vector Service retrieves context

LLM generates response

Stream response to frontend
Rationale: Real-time interaction with context-aware responses

6. Package Structure
kollektiv/
├── src/
│   ├── models/           # All data models
│   │   ├── domain/      # Core business objects
│   │   │   ├── content.py    # Document, Chunk models
│   │   │   ├── search.py     # Search, Result models
│   │   │   ├── chat.py       # Session, Message models
│   │   │   └── user.py       # User, Usage models
│   │   ├── api/         # API request/response models
│   │   │   ├── content.py    # Content API models
│   │   │   ├── chat.py       # Chat API models
│   │   │   └── user.py       # User API models
│   │   └── events/      # Event/message models
│   │       ├── jobs.py       # Job events
│   │       └── updates.py    # Status updates
│   │
│   ├── core/            # Core application code
│   │   ├── exceptions/  # Custom exceptions
│   │   │   ├── base.py      # Base exceptions
│   │   │   └── handlers.py  # Exception handlers
│   │   ├── interfaces/  # Abstract interfaces
│   │   │   ├── repository.py
│   │   │   └── service.py
│   │   └── services/    # Service implementations
│   │       ├── content.py
│   │       ├── vector.py
│   │       └── chat.py
│   │
│   ├── api/            # API layer
│   │   ├── routes/     # Route definitions
│   │   │   ├── content.py
│   │   │   ├── chat.py
│   │   │   └── user.py
│   │   ├── webhooks/   # Webhook handlers
│   │   │   └── firecrawl.py
│   │   └── middleware/ # API middleware
│   │       ├── auth.py
│   │       └── error.py
│   │
│   ├── infrastructure/ # Infrastructure concerns
│   │   ├── config.py   # Configuration
│   │   ├── logging.py  # Logging setup
│   │   └── queue.py    # Job queue
│   │
│   └── utils/         # Shared utilities
│       ├── validation.py
│       └── helpers.py

7. API Management
API Versioning

URL-based: /api/v1/

Clear version migration strategy

Route Organization
/api/v1/
├── content/   # Content management
│   ├── POST /crawl     # Start crawling
│   ├── GET  /status    # Check status
│   └── GET  /documents # List documents
├── chat/      # Chat operations
│   ├── POST /message   # Send message
│   └── GET  /stream    # SSE endpoint
├── user/      # User operations
└── admin/     # Admin functions

Webhook Handling
/webhooks/
├── firecrawl/  # FireCrawl callbacks
└── llm/        # LLM provider webhooks

8. Deployment & Integration Model
Application Architecture
Single Application Approach (Selected)

One FastAPI application containing all services

Services as internal Python modules

Direct method calls between services

Rationale:

Simpler deployment

Easier development

Reduced operational complexity

Suitable for initial scale (10-1000 users)

Infrastructure Components

ChromaDB: Embedded mode initially

Runs within main application

Local persistence

Can be extracted to separate service later

Rationale: Simplifies deployment, sufficient for initial scale

Redis: Railway.app Redis instance

Deployed alongside main application

Built-in Redis support from Railway

Simple configuration

Rationale:

Single platform management

Simplified operations

Cost-effective

Automatic backups

Supabase: Managed service

Handles auth and data storage

Provides row-level security

Deployment Configuration
Railway.app Deployment



Railway Project
├── FastAPI Application
│   ├── API Server
│   ├── Background Workers
│   └── Embedded ChromaDB
└── Redis Instance
    ├── Job Queue
    └── Pub/Sub
External Services



External Dependencies
└── Supabase (Managed)
    ├── PostgreSQL
    └── Auth
Scaling Considerations
Initial Setup

Single application instance

Multiple worker processes

Embedded ChromaDB

Managed Redis/Supabase

Future Scale Options

Extract ChromaDB to separate service

Multiple application instances

Load balancer addition

Dedicated worker servers

9. Key Technical Decisions
Application Design
Single FastAPI application with embedded ChromaDB

Direct service communication (no internal API)

Background processing via Redis queues
Rationale: Maximum simplicity for initial scale (1000 users), clear path to scale out

Data Management
Supabase: User data, auth, metadata

ChromaDB: Document vectors, search indices

Redis: Job queues, real-time features
Rationale: Managed services where possible, embedded where simple

Error Handling & Recovery
Domain exceptions propagate to global handlers

Retries for external services (LLM, crawling)

Failed jobs move to DLQ for inspection

Errors logged with context for debugging
Rationale: Fail fast, recover automatically where possible

Multi-tenancy
Per-user ChromaDB collections

Row-level security in Supabase

Resource quotas enforced in application
Rationale: Simple but effective data isolation

Security Model
Supabase handles auth, JWT validation

Service-level RBAC enforcement

All external comms over TLS
Rationale: Leverage battle-tested solutions

Performance & Scaling
Sub-second search response target

Async processing for long operations

Horizontal scaling via multiple instances
Rationale: Good UX without premature optimization

10. Development Roadmap
Initial Release: Core RAG
Focus on essential RAG functionality with basic user management.
Key capabilities: document processing, vector search, chat interface.
Success criteria: working end-to-end RAG pipeline.

Feature Enhancement
Improve core RAG quality through better chunking and search.
Add streaming responses and progress tracking.
Measure and optimize based on user feedback.

Production Hardening
Scale to multi-user support with proper isolation.
Implement monitoring and performance optimization.
Establish operational procedures and documentation.

11. Operations & Quality
Development Environment
Poetry manages dependencies and virtual environments.
Local services (Redis, ChromaDB) for development independence.
Supabase CLI enables offline auth development.

Testing & Quality
Service-level unit tests verify core logic.
Integration tests ensure service interactions.
RAG-specific tests validate search and response quality.

Monitoring & Reliability
Health checks track service and dependency status.
Performance metrics focus on response times and queue health.
Structured logging enables effective debugging.

Backup & Recovery
Daily snapshots of ChromaDB vectors.
Supabase handles relational data backups.
Regular recovery testing ensures data safety.
