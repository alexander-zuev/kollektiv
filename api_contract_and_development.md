# API Contract and Development Process

This document outlines the process for defining API contracts and developing features for our application. It emphasizes a structured approach to ensure smooth integration between the frontend and backend.

## 1. API Contract Definition

The API contract is the cornerstone of communication between the frontend and backend. It's a formal agreement that specifies:

- **Endpoints:** The URLs where the frontend sends requests.
- **Request Methods:** HTTP methods (GET, POST, PUT, DELETE, etc.).
- **Request Data:** Format of data sent in the request body, including data types and validation rules (using JSON Schema or TypeScript interfaces).
- **Response Data:** Format of data returned in the response, including data types, status codes, and error handling.
- **Authentication:** How the frontend authenticates with the backend (e.g., API keys, JWT tokens, OAuth 2.0).
- **Versioning:** How API changes are managed over time (e.g., using version numbers in the URL or headers).

### 1.1. Contract Structure

Each endpoint in the API contract should be documented as follows:

````
#### Endpoint: [HTTP Method] [URL Path]

**Purpose:** [Brief description of the endpoint's functionality]

**Request:**

-   **Headers:**
    -   [Header Name]: [Description, e.g., Content-Type: application/json]
    -   [Header Name]: [Description, e.g., Authorization: Bearer <token>]
-   **Path Parameters:**
    -   `{parameter_name}`: [Description, data type, e.g., {user_id}: User ID (UUID)]
-   **Query Parameters:**
    -   `parameter_name`: [Description, data type, required/optional, e.g., limit: Number of items to return (integer, optional)]
-   **Request Body:**
    ```typescript
    // TypeScript interface or JSON Schema defining the request body structure
    interface RequestBody {
      property1: string; // Description of property1
      property2: number; // Description of property2
      // ... other properties
    }
    ```

**Response:**

-   **Success Response (e.g., 200 OK, 201 Created, 204 No Content):**
    ```typescript
    // TypeScript interface or JSON Schema defining the success response body
    interface SuccessResponse {
      property1: string; // Description of property1
      property2: number; // Description of property2
      // ... other properties
    }
    ```
-   **Error Responses:**
    -   **[Status Code, e.g., 400 Bad Request]:** [Description of the error]
        ```typescript
        // TypeScript interface or JSON Schema for the error response body
        interface ErrorResponse {
          error: string; // Error code or message
          detail?: string; // Optional detailed error description
        }
        ```
    -   **[Status Code, e.g., 401 Unauthorized]:** [Description of the error]
    -   **[Status Code, e.g., 404 Not Found]:** [Description of the error]
    -   **[Status Code, e.g., 500 Internal Server Error]:** [Description of the error]

**Examples:**

-   **Request Example:**
    ```json
    {
      "property1": "value1",
      "property2": 123
    }
    ```
-   **Success Response Example:**
    ```json
    {
      "property1": "result1",
      "property2": 456
    }
    ```
-   **Error Response Example:**
    ```json
    {
      "error": "INVALID_INPUT",
      "detail": "Property 'property1' must be a string"
    }
    ```
````

### 1.2. Existing Chat API Contract

Based on your current implementation (`chat_models.py`, `chat_schemas.py`, `chat.py`, `chat_service.py`), here's the API contract for your chat feature:

#### Endpoint: `POST /api/v0/chat`

**Purpose:** Send a user message to the AI assistant and receive a streaming response.

**Request:**

- **Headers:**

  - `Content-Type: application/json`

- **Request Body:**

  ```typescript
  interface UserMessage {
    user_id: string; // UUID of the user from Supabase
    message: string; // User's message
    conversation_id?: string; // UUID of the conversation (optional, for new conversations)
    data_sources: string[]; // List of data source IDs - currently not used in backend
  }
  ```

**Response:**

- **Type:** `EventSourceResponse` (Server-Sent Events)
- **Event Types:**

  ```typescript
  type MessageType =
    | "TEXT_TOKEN" // Part of the assistant's response
    | "TOOL_USE" // Indicates the assistant is using a tool
    | "TOOL_RESULT" // Result from a tool
    | "CONVERSATION_ID" // ID of the conversation
    | "DONE" // End of the stream - NOT CURRENTLY IMPLEMENTED
    | "ERROR"; // An error occurred

  interface LLMResponse {
    message_type: MessageType;
    text: string | object; // Content of the event
  }
  ```

- **Example Events:**

  ```javascript
  // TEXT_TOKEN
  data: {"message_type": "TEXT_TOKEN", "text": "Hello"}

  // TOOL_USE
  data: {"message_type": "TOOL_USE", "text": {"tool_name": "rag_search", "input": {"query": "some query"}}}

  // CONVERSATION_ID
  data: {"message_type": "CONVERSATION_ID", "text": "your_conversation_id"}

  // TOOL_RESULT
  data: {"message_type": "TOOL_RESULT", "text": {"result": "some result"}}

  // ERROR
  data: {"message_type": "ERROR", "text": "An error occurred"}
  ```

**Error Handling:**

- **400 Bad Request:** If the request body is invalid (handled by FastAPI's validation).
- **500 Internal Server Error:**
  - `RetryableLLMError`: A retryable error occurred in the `llm_assistant`.
  - `NonRetryableLLMError`: A non-retryable error occurred in the `llm_assistant`.
  - Other exceptions during message processing.

**Notes:**

- The `data_sources` field in the `UserMessage` is not currently used in the backend implementation.
- The `DONE` event type is defined in `MessageType` but is not explicitly sent by the `ChatService`. You might want to add a `MESSAGE_STOP` or similar event to signal the end of the stream.
- The current implementation does not handle specific headers beyond `Content-Type`.
- Authentication is likely handled at the infrastructure level (e.g., Supabase RLS), but it's not explicitly defined in this endpoint's contract.

#### Endpoint: `GET /api/v0/conversations`

**Purpose:** Get a list of conversations for the authenticated user.

**Request:**

- **Headers:**
  - `Authorization: Bearer <user_token>` (Assuming Supabase authentication)

**Response:**

```typescript
interface ConversationListResponse {
  recent: ConversationGroup;
  last_month: ConversationGroup;
  older: ConversationGroup;
}

interface ConversationGroup {
  time_group: "Last 7 days" | "Last 30 days" | "Older";
  conversations: ConversationSummary[];
}

interface ConversationSummary {
  conversation_id: string;
  title: string;
  data_sources: string[];
}
```

**Error Handling:**

- **401 Unauthorized:** If the user is not authenticated.
- **500 Internal Server Error:** For database or other server errors.

#### Endpoint: `GET /api/v0/conversations/{conversation_id}`

**Purpose:** Get all messages for a specific conversation.

**Request:**

- **Headers:**
  - `Authorization: Bearer <user_token>`
- **Path Parameter:**
  - `{conversation_id}: string` (UUID of the conversation)

**Response:**

```typescript
interface ConversationMessages {
  messages: ConversationMessage[];
}

interface ConversationMessage {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: MessageContent;
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp
}

interface MessageContent {
  blocks: ContentBlock[];
}

interface ContentBlock {
  type: string;
  text?: string;
  tool_name?: string;
  tool_input?: object;
  tool_use_id?: string;
  content?: string | object;
  is_error?: boolean;
}
```

**Error Handling:**

- **401 Unauthorized:** If the user is not authorized to access this conversation.
- **404 Not Found:** If the conversation does not exist.
- **500 Internal Server Error:** For database or other server errors.

## 2. Feature Development Process

This is a step-by-step guide for building new features, integrating the frontend and backend effectively.

### Step 1: Define the Feature and API Contract

1. **Feature Idea:** Clearly describe the feature, its purpose, and the problem it solves.
2. **User Stories:** Write user stories to capture how users will interact with the feature.
3. **API Contract:**
   - Define new endpoints or changes to existing ones, following the structure outlined in Section 1.1.
   - Specify request and response formats using TypeScript interfaces or JSON Schema.
   - Document authentication and error handling.

### Step 2: Backend Implementation

1. **Database Schema:**

   - If needed, update your database schema (e.g., using SQL migrations in Supabase).
   - Ensure your schema changes align with the API contract and support the feature's data requirements.

2. **Pydantic Models:**

   - Create or update Pydantic models in `src/models/` to represent data structures.
   - Use these models for:
     - Data validation in API endpoints.
     - Defining the structure of data stored in the database.

3. **API Endpoints:**

   - Implement new API endpoints in `src/api/v0/endpoints/` using FastAPI.
   - Use the Pydantic models to validate request data and format responses.
   - Handle authentication and authorization (e.g., using Supabase RLS policies).

4. **Service Layer (e.g., `ChatService`):**

   - Implement the core business logic for your feature in service classes.
   - This layer interacts with the database, external services (like the `llm_assistant`), and other components.

5. **Error Handling:**
   - Define custom exception classes (like `NonRetryableLLMError`) for specific error scenarios.
   - Handle errors gracefully in your API endpoints and return appropriate HTTP status codes and error messages, as defined in the API contract.

### Step 3: Frontend Integration

1. **TypeScript Interfaces:**

   - Create TypeScript interfaces that mirror the API contract's request and response models.
   - These interfaces will ensure type safety when making API calls from the frontend.

2. **API Client:**

   - Write functions (or use a library like `axios`) to make API requests from your React components.
   - Use the TypeScript interfaces to type-check the data sent to and received from the API.

3. **React Components:**

   - Design and implement React components that interact with the API.
   - Handle loading states, errors, and user interactions.

4. **State Management:**
   - Use a state management solution (like React Context, Redux, or Zustand) to manage the application's state, including data fetched from the API.

### Step 4: Testing

1. **Backend Tests:**

   - Write unit tests for your Pydantic models, API endpoints, and service layer logic.
   - Use a testing framework like `pytest`.

2. **Frontend Tests:**

   - Write unit tests for your React components and API client functions.
   - Use a testing framework like `Jest` and a testing library like `React Testing Library`.

3. **Integration Tests:**
   - Test the interaction between the frontend and backend.
   - You can use tools like `Cypress` or `Playwright` for end-to-end testing.

### Step 5: Deployment

1. **Backend Deployment:**

   - Deploy your backend code to a server (e.g., using Docker and a cloud provider).

2. **Frontend Deployment:**
   - Build your React application and deploy it to a hosting service (e.g., Vercel, Netlify, or AWS S3).

## 3. Example: Adding a "Delete Conversation" Feature

Let's apply this process to a new feature: deleting a conversation.

### Step 1: Define the Feature and API Contract

**Feature Idea:** Allow users to delete a conversation.

**User Story:** As a user, I want to delete a conversation so that I can remove unwanted conversations from my history.

**API Contract:**

#### Endpoint: `DELETE /api/v0/conversations/{conversation_id}`

**Purpose:** Delete a conversation.

**Request:**

- **Headers:**
  - `Authorization: Bearer <user_token>`
- **Path Parameter:**
  - `{conversation_id}: string` (UUID of the conversation)

**Response:**

- **Status Codes:**
  - `204 No Content`: If the conversation was deleted successfully.
  - `401 Unauthorized`: If the user is not authorized to delete this conversation.
  - `404 Not Found`: If the conversation does not exist.
  - `500 Internal Server Error`: For other server errors.

### Step 2: Backend Implementation

1. **Database Schema:** No changes needed (assuming you have a `conversations` table).

2. **Pydantic Models:** No changes needed.

3. **API Endpoint:**

   ```python:src/api/v0/endpoints/chat.py
   from uuid import UUID

   from fastapi import APIRouter, HTTPException

   from src.api.dependencies import ChatServiceDep
   from src.api.routes import V0_PREFIX, Routes

   # ... existing routers ...

   @conversations_router.delete(Routes.V0.Conversations.DELETE)
   async def delete_conversation(conversation_id: UUID, chat_service: ChatServiceDep) -> None:
       """Delete a conversation."""
       try:
           await chat_service.delete_conversation(conversation_id)
       except Exception as e:
           raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {e}")
   ```

4. **Service Layer:**

   ```python
   # Add to ChatService class in src/core/chat/chat_service.py
   async def delete_conversation(self, conversation_id: UUID):
       """Deletes a conversation from the database.

       Args:
           conversation_id: The ID of the conversation to delete.

       Raises:
           Exception: If there is an error deleting the conversation.
       """
       try:
           async with self.db.get_connection() as conn:
               # Assuming you have a method to delete a conversation by ID
               await conn.execute(
                   "DELETE FROM chat.conversations WHERE conversation_id = $1",
                   str(conversation_id),
               )
       except Exception as e:
           logger.error(f"Error deleting conversation: {e}")
           raise
   ```

5. **Error Handling:** Handled by the `try...except` block in the API endpoint.

### Step 3: Frontend Integration

1. **TypeScript Interfaces:** No new interfaces needed.

2. **API Client:**

   ```typescript
   // Add to your API client functions
   async function deleteConversation(conversationId: string): Promise<void> {
     const response = await fetch(`/api/v0/conversations/${conversationId}`, {
       method: "DELETE",
       headers: {
         Authorization: `Bearer ${getAuthToken()}`, // Get user token
       },
     });

     if (!response.ok) {
       const errorData = await response.json();
       throw new Error(errorData.detail || "Failed to delete conversation");
     }
   }
   ```

3. **React Components:**
   - Add a "Delete" button to your `ConversationSummary` component.
   - Call the `deleteConversation` function when the button is clicked.
   - Update the UI to remove the deleted conversation.

### Step 4: Testing

1. **Backend Tests:**

   - Write a test for the `delete_conversation` endpoint and service method.
   - Test success, unauthorized, not found, and server error cases.

2. **Frontend Tests:**
   - Test the `deleteConversation` API client function.
   - Test the React component that calls this function.

### Step 5: Deployment

1. Deploy the updated backend and frontend code.

## 4. Conclusion

This document provides a comprehensive guide for defining API contracts and developing features in our application. By following this structured process, we can ensure clear communication between the frontend and backend, leading to a more maintainable and scalable application. Remember to keep the API contract as the single source of truth and to thoroughly test all new features before deployment.
