# Kollektiv System Design

## 1. Introduction and Goals

Kollektiv is a platform for building and deploying RAG-powered chatbots, targeting two main user groups:

1. **End Users:** Individuals who want to easily create and customize chatbots that can access and reference various content for contextually rich replies, starting with web content. This is achieved through a user-friendly web application.

2. **Developers (Future):** Developers who want to integrate RAG capabilities into their applications using a robust and scalable API service. This service will manage the entire RAG pipeline, including content syncing, referencing, and retrieval, also initially focusing on web content.

This document details the architecture and design of the Kollektiv web application, with considerations for its future evolution into a comprehensive platform including the API service.

### 1.1 Goals and Objectives

* **Short-Term:** Deliver a functional and intuitive web application enabling end-users to create and deploy RAG-powered chatbots with web content integration.
* **Long-Term:** Expand Kollektiv into a platform offering both a web application and API service, supporting diverse content sources and advanced RAG features.

### 1.2 User Personas

* **Web App User:** Non-technical users seeking a simple way to create and configure chatbots, manage content sources, and customize responses.
* **API User:** Developers needing a reliable and scalable API for integrating RAG functionalities into their applications.

## 2. Architecture Overview

### 2.1 Architectural Style

Kollektiv adopts a layered architecture with an API-first approach. This promotes separation of concerns, maintainability, and facilitates the future development of the API service. The layers interact as follows:

* **Interface Layer (`api`):** Provides external access points, including API endpoints for various clients (web app, future API users) and the web user interface. It interacts with the Application Services layer.

* **Application Services Layer (`services`):** Orchestrates business logic, manages interactions between domains (content, knowledge, chat), and interacts with the Domain Logic layer.

* **Domain Logic Layer (`core`):** Encapsulates the core business rules and operations for each domain, interacting with Domain Models and the Infrastructure layer.

* **Domain Models Layer (`models`):** Defines data structures and models used across the application, independent of specific domain logic.

* **Infrastructure Layer (`infrastructure`):** Offers technical services and utilities, including data storage, external service integrations (Firecrawl, Anthropic, Cohere), and logging.

### 2.2 Key Architectural Decisions

* **Layered Architecture:** Chosen for separation of concerns, maintainability, and testability.
* **API-First Approach:** Enables future expansion into a standalone API service and supports diverse client interfaces.
* **Asynchronous Processing:** Handles time-consuming tasks like web crawling and embedding generation asynchronously to maintain application responsiveness. Redis queues manage these asynchronous operations.
* **Modular Design:** Allows independent development, testing, and deployment of individual components. This modularity is reflected in the package structure, separating concerns by domain and layer.

## 3. Logical View: Domain Model and Relationships

This section describes the key domains, their components, and how they interact to fulfill Kollektiv's functionalities. Understanding these relationships is crucial for designing a cohesive and maintainable system.

### 3.1 Core Domains

1. **Content Management:** Responsible for acquiring, processing, and managing content from various sources (currently web pages).
    * **Components:** Crawler, Chunker, Embedder, Content Repository.
    * **Responsibilities:**
        * Fetching content from URLs.
        * Splitting content into manageable chunks.
        * Generating embeddings for each chunk.
        * Storing and managing content metadata and versions.

2. **Knowledge Engine:**  Manages the knowledge base, including vector embeddings and search functionality.
    * **Components:** Vector Database, Search Index, Ranking Engine.
    * **Responsibilities:**
        * Storing and managing vector embeddings.
        * Indexing content for efficient search.
        * Performing similarity searches and ranking results.

3. **Chat Interface:** Handles user interactions and chatbot responses.
    * **Components:** Chat Session Manager, Response Generator, Streaming Service.
    * **Responsibilities:**
        * Managing chat sessions and context.
        * Generating chatbot responses based on user queries and retrieved knowledge.
        * Streaming responses in real-time.

4. **System Core:**  Provides cross-cutting functionalities and manages system-level concerns.
    * **Components:** Job Manager, Event Handler, Configuration Manager.
    * **Responsibilities:**
        * Orchestrating jobs and tasks.
        * Handling system events and notifications.
        * Managing application configuration and settings.


### 3.2 Domain Interactions

The domains interact to provide the core functionality of Kollektiv:

1. **Content Management → Knowledge Engine:**  Processed and chunked content from Content Management is sent to the Knowledge Engine for embedding generation and indexing.  Content updates trigger re-indexing.

2. **Knowledge Engine → Chat Interface:** The Chat Interface queries the Knowledge Engine for relevant information based on user input.  The Knowledge Engine returns ranked search results.

3. **System Core ↔ All Domains:** The System Core coordinates operations across all domains, manages job execution, handles events, and provides configuration settings.

**Diagram (Recommended):**

Consider adding a diagram here to visually represent the domain interactions and data flow.  A simple diagram can significantly improve understanding.  For example, you could use a sequence diagram or a context diagram.


## 4. Development View: Package Structure and Implementation

### 4.1 Architectural Pattern: Layered Architecture and Design Patterns

Kollektiv follows a layered architecture to promote separation of concerns and maintainability. This architecture is further enhanced by incorporating specific design patterns within each layer:

* **Interface Layer (`api`):**  Utilizes the **Controller** pattern.  Controllers act as intermediaries between external requests (from the web app or API clients) and the application's internal logic. They handle routing, input validation, data transformation, and orchestrate the execution of appropriate application services.  This keeps the interface layer thin and focused on presentation, delegating business logic to the services layer.  *Implementation:*  Each API endpoint is handled by a dedicated controller function within the `api/v0` directory, organized by domain.

* **Application Services Layer (`services`):** Employs the **Service Orchestrator** pattern.  Service orchestrators coordinate complex workflows and transactions that span multiple domains. They manage dependencies between domain services, ensuring data consistency and transactional integrity.  This pattern centralizes complex logic, making it easier to manage and test.  *Implementation:* Services are defined in the `services` directory (e.g., `services/content_service.py`).  They interact with multiple domain services to implement complete user journeys.

* **Domain Logic Layer (`core`):**  Implements core business rules using several patterns:
    * **Strategy:** Used for content chunking and embedding generation.  The Strategy pattern defines a family of algorithms (different chunking or embedding methods), encapsulates each one, and makes them interchangeable.  This allows for flexibility in choosing the best algorithm for a given context.  *Implementation:*  Different chunking and embedding strategies can be implemented as separate classes, adhering to a common interface.
    * **Repository:** Used for data access.  The Repository pattern abstracts the underlying data storage mechanism (ChromaDB, Redis, Supabase) from the domain logic.  This promotes data access consistency and simplifies testing.  *Implementation:*  Repositories are defined in the `infrastructure/storage` directory, providing a consistent interface for accessing different data stores.

* **Domain Models Layer (`models`):**  Uses **Plain Old Python Objects (POPOs)** or **Data Transfer Objects (DTOs)**.  These simple objects represent data structures and are used for data transfer between layers.  They are primarily data containers and do not contain business logic.  *Implementation:*  Models are defined in the `models` directory, organized by domain.  Pydantic is used for data validation and serialization.

* **Infrastructure Layer (`infrastructure`):**  Implements technical services and utilities using these patterns:
    * **Repository (as mentioned above):**  Abstracts data access.
    * **Adapter/Facade:** Used for external service integrations (Firecrawl, Anthropic, Cohere).  These patterns provide a simplified interface to complex external services, decoupling the application from the specifics of the external API.  *Implementation:*  Adapters or facades are defined in the `infrastructure/external` directory.
    * **Singleton:** Used for logging.  Ensures that there is only one instance of the logger, providing a consistent logging interface across the application.  *Implementation:*  A single logger instance is typically initialized in the `infrastructure/common/logging.py` module.

This combination of layered architecture and design patterns ensures a clear separation of concerns, promotes code reusability, and enhances maintainability.

### 4.2 Layer Definitions and Implementation Guide

The layers are further broken down into specific packages:

* **`api`:**  Exposes API endpoints for interacting with Kollektiv.
    * `v0`:  Contains the current version of the API.
        * `content`: Endpoints related to content management.
        * `chat`: Endpoints related to chat interactions.
        * `system`: Endpoints for system-level operations.
* **`services`:** Orchestrates complex operations and interacts with multiple domains.
    * `content_service.py`: Manages content sources and crawling.
    * `search_service.py`: Handles search queries and knowledge retrieval.
    * `chat_service.py`: Manages chat sessions and interactions.
* **`core`:** Contains the core business logic of the application.
    * `content`:  Handles content processing and crawling.
        * `crawler.py`: Implements the web crawling logic.
        * `embedder.py`: Handles embedding generation logic.
    * `knowledge`: Manages knowledge base operations.
        * `search.py`: Implements search functionality.
        * `vectors.py`: Handles vector embeddings and storage.
    * `chat`:  Manages chat sessions and interactions.
        * `session.py`: Handles chat session management.
        * `generation.py`: Handles response generation.
* **`models`:** Defines data structures and models used across the application.
    * `content`: Models related to content.
        * `document.py`: Defines the structure of a document.
        * `chunk.py`: Defines the structure of a content chunk.
    * `knowledge`: Models related to knowledge.
        * `embedding.py`: Defines the structure of a vector embedding.
        * `search_result.py`: Defines the structure of a search result.
    * `chat`: Models related to chat.
        * `message.py`: Defines the structure of a chat message.
        * `session.py`: Defines the structure of a chat session.
* **`infrastructure`:** Provides technical services and utilities.
    * `storage`: Implementations for different storage backends.
        * `chroma.py`: ChromaDB implementation.
        * `redis.py`: Redis implementation.
    * `external`: Integrations with external services.
        * `firecrawl.py`: Integration with the Firecrawl API.
    * `config`: Configuration management.
    * `common`: Shared utilities and helpers.

### 4.3 API Design and Management

API endpoints are versioned and organized by domain within the `api/v0` directory. Each domain has its own subdirectory containing routes and schemas. This modular approach promotes maintainability and scalability.

* **Routing:** Routes are defined using FastAPI's routing mechanisms within each domain's `routes.py` file.  This decentralized approach allows for better organization and scalability compared to a centralized routing scheme.

* **Schemas:** Request and response models (schemas) are defined using Pydantic in each domain's `schemas.py` file, co-located with the routes they serve.

* **API Structure:**

```
/api/v0/
├── content/
│   ├── routes.py
│   ├── schemas.py
│   ├── POST /crawl  (Initiates a crawl job)
│   ├── GET /jobs/{job_id}/status (Gets the status of a crawl job)
│   └── GET /sources/{source_id} (Retrieves crawled data for a source)
├── chat/
│   ├── routes.py
│   ├── schemas.py
│   ├── POST /message (Sends a message to the chatbot)
│   └── GET  /stream (Streams chatbot responses)
└── system/
    ├── routes.py
    ├── schemas.py
    └── POST /webhooks/firecrawl (Receives Firecrawl webhooks)
```

* **Webhook Integration:**  Firecrawl webhooks are handled by the `/system/webhooks/firecrawl` endpoint.  This endpoint updates the job status and triggers subsequent processing steps.


## 5. Process View: Data Flow and Key Considerations

This section outlines the key processes and runtime components within Kollektiv, highlighting important considerations for data flow, asynchronous operations, and error handling. Detailed process flows for specific features will be documented separately.

### 5.1 Runtime Components

Kollektiv consists of the following key runtime components:

* **FastAPI Application:** The central hub, handling API requests, routing, background tasks, and component interaction.

* **Redis:**  An in-memory data store used for job queues (asynchronous tasks), caching, and real-time updates.

* **ChromaDB:**  The vector database for storing and managing vector embeddings, enabling efficient similarity search.  Currently embedded, but scalable to a separate service.

* **Supabase:**  Provides persistent data storage (content metadata, user data), authentication, and authorization.

* **Firecrawl, Anthropic, Cohere (External Services):**  Respectively handle web crawling, LLM response generation, and NLP services.  Interacted with via their APIs.

### 5.2 Asynchronous Processing with Redis Queues

Kollektiv leverages asynchronous processing for long-running tasks such as web crawling and embedding generation. This ensures that the application remains responsive to user requests while these tasks are being executed in the background. Redis queues are used to manage these asynchronous operations.  A worker process consumes tasks from the queue and executes them.

### 5.3 Key Process Considerations

* **Content Acquisition:**  The process begins with a user providing a URL. The crawler fetches the content, which is then chunked and embedded.  These steps are executed asynchronously.
* **Knowledge Storage:**  Chunks and their corresponding embeddings are stored in the vector database (ChromaDB) for efficient retrieval. Metadata and versioning information are stored in a persistent data store (Supabase).
* **Query Processing:**  User queries are processed by expanding them, performing similarity searches against the vector database, and ranking the results.
* **Response Generation:**  The chatbot generates responses based on the ranked results and the conversation context.  Responses are streamed back to the user in real-time.
* **Webhook Handling:**  Webhooks from external services (e.g., Firecrawl) are processed asynchronously to update job statuses and trigger subsequent processing steps.

### 5.4 Error Handling, Logging, Monitoring, and Alerting

Kollektiv employs a comprehensive approach to error handling, logging, monitoring, and alerting to ensure system reliability and maintainability.

* **Error Handling:**  Each layer of the application implements appropriate error handling mechanisms.  Transient errors (e.g., network issues, temporary API unavailability) are handled with retries.  Persistent errors are logged, and appropriate error messages are returned to the user or calling service.  Custom exceptions are used to provide specific error information.

* **Logging:**  Structured logging is used to capture detailed information about system events, errors, and performance.  Logs include timestamps, severity levels, relevant context information, and stack traces for debugging.  Logs are stored centrally and can be analyzed for trends and patterns.

* **Monitoring:**  Key metrics, such as job processing times, error rates, API response times, and resource utilization, are continuously monitored.  This allows for proactive identification of potential issues and performance bottlenecks.

* **Alerting:**  Automated alerts are triggered for critical errors and performance degradations.  Alerts are sent to administrators via appropriate channels (e.g., email, Slack) to enable timely intervention and resolution.


## 6. Use Case View

This section describes a few key use cases to illustrate how users interact with Kollektiv:

* **Adding a Content Source:** A user provides a URL to a documentation website.  Kollektiv crawls the website, extracts content, chunks it, generates embeddings, and stores them in the vector database.

* **Searching for Information:** A user enters a natural language query.  Kollektiv expands the query, performs a similarity search against the vector database, re-ranks the results, and returns the most relevant content.

* **Chatting with the AI Assistant:** A user interacts with the AI assistant in a chat interface.  The assistant uses the knowledge base to provide context-aware responses to the user's queries.

## 7. Physical View

### 7.1 Application Architecture

Kollektiv is deployed on Railway.  The infrastructure consists of:

* **FastAPI Application:**  Handles API requests, background tasks, and communication with other services.
* **Redis:**  Used for job queues, caching, and real-time updates.
* **ChromaDB:**  Stores vector embeddings and facilitates similarity search.  Currently embedded within the FastAPI application, but can be separated for scalability.
* **Supabase:**  Provides authentication and persistent data storage.

### 7.2 Infrastructure

Kollektiv is deployed on Railway.  The infrastructure consists of:

* **FastAPI Application:**  Handles API requests, background tasks, and communication with other services.
* **Redis:**  Used for job queues, caching, and real-time updates.
* **ChromaDB:**  Stores vector embeddings and facilitates similarity search.  Currently embedded within the FastAPI application, but can be separated for scalability.
* **Supabase:**  Provides authentication and persistent data storage.

### 7.3 Deployment Process

... (Add details about your deployment process, including CI/CD, environment configuration, etc.)

## 8. Cross-Cutting Concerns

### 8.1 Error Handling and Logging

... (Expand on error handling strategies, logging levels, and monitoring tools.)

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

## 9. Performance and Scalability

### 9.1 Performance Strategy

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

### 9.2 Scalability

**Vector Store Separation:**  >100K documents
**Service Extraction:**  >1000 concurrent users
**Load Balancing:**  >100 req/s

## 10. Quality Assurance

**Testing Strategy**
Decision: Focus on domain logic and RAG quality
Key Areas:
- Domain model behavior
- Processing pipeline reliability
- RAG response quality
- Integration points
- **Unit, Integration, and E2E test coverage as described in Section 4.2.**  This ensures comprehensive testing across all layers of the application.

**RAG Quality Metrics**
Primary:
- Answer relevance (>90%)
- Context accuracy (>95%)
- Response coherence
Implementation: Ragas-based evaluation suite

## 11. Future Enhancements

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

## 12. Implementation Details

### 12.1 Modules and Responsibilities

This section details the key modules and their responsibilities within Kollektiv's layered architecture.  The structure follows the domain-driven design principles and the chosen design patterns (see Section 4.1).

* **`api` (Interface Layer):**  Handles external interactions.
    * `v0/*/<domain>/routes.py`:  API endpoints for each domain, using FastAPI.
    * `v0/*/<domain>/schemas.py`:  Pydantic schemas for request/response validation.

* **`services` (Application Services Layer):** Orchestrates domain logic.
    * `<domain>_service.py`:  Service orchestrators for each domain, managing complex workflows.

* **`core` (Domain Logic Layer):** Implements core business rules.
    * `content/*`:  Content processing logic (crawling, embedding).
    * `knowledge/*`: Knowledge base management (search, ranking).
    * `chat/*`: Chat session and response generation logic.

* **`models` (Domain Models Layer):**  Pydantic models for data representation, organized by domain.

* **`infrastructure` (Infrastructure Layer):**  Provides technical services.
    * `storage/*`: Data access implementations (ChromaDB, Redis, Supabase).
    * `external/*`: Adapters for external services (Firecrawl, Anthropic, Cohere).
    * `config`: Configuration management.
    * `common/logging.py`:  Logging setup and configuration.


### 12.2 Asynchronous Task and Job Management

Asynchronous tasks (crawling, embedding, webhooks) are managed using Redis queues.  The `JobManager` (System Core) handles task creation, queuing, monitoring, and status tracking.  Results are stored for retrieval.  This asynchronous approach ensures application responsiveness during long-running operations.

[End of document]
