
Goal:
- Allow LLM assistant to know what sources are available

Context:
- LLMs have system prompt and access to tools. If system prompt does not have any information about source, LLMs might misused the tools because they don't know what sources are available.
- On the other hand, my application most likely will use users with only a few active sources. However, I am sure this is not the only approach to handling RAG.

Approach:
- Generate LLM based summary of each added data source
- Get a list of all source_urls
- Get n_chunks randomly
- Generate a summary which consists of:
-- A paragraph describing the source
-- A list of keywords or kery topics

Lifecycle:
- Creation:
-- Should be generated generated along with adding chunks to the vector database (can be in paralell)
- Update
-- No mechanism to update a source, hence the data source summary for now
- Deletion
-- Should be deleted when a source is deleted

Storage:
- User adds a source
- At this point summary should be added and saved to the LLM assistant
- Summary can be persisted to supabase for simplicity (no Redis cache)
- For simplicity, adding or removing a source should trigger incremental summary updates (loading / unloading)
- If you proove that I can very simply use Redis cache, then I can use it in addition to Supabase, but I fear for the need to syncronize the state. Although it should be easy to do.

Questions to you:
- Do you think this appraoch makes sense? - Yes
- How else in RAG systems this problem is solved? - Agentic RAG, dynamic indexing, others.
- Which endpoint and method should handle the update of the data sources linked to a conversation?


Lifecycle:
- Activation of a data source
-- If the source doesn't exist, it is created first
-- Users then activate the sources in the data source management UI
-- Each conversation will have a mapping of IDs of data sources that are active for that conversation
-- When a user loads a conversation, a Conversation object holds the list of IDs of data sources that are active for that conversation
-- At this point, the summary is retrieved from Supabase, and added to the system prompt
-- System prompt limit for:
--- Anthropic = shared with the context (200k)


- Switching between conversations
-- When a user switches between conversations, ChatService will fetch conversation, summaries, update system prompt
- Deactivating of a data source
-- When a user deselects a data source, XXX endpoint (which one??) will trigger which method (??)

How to ensure fast loading:
- Batch loading of the conversation and it's active summaries into the system prompt
- Structure data efficiently - separate table with conversation id and source id mappings. Create an index on the conversation id.

API endpoints:
PUT /api/v0/conversations/{conversation_id}/sources
- Handles activation and deactivation of a data source
- Accepts a list of active source ids
- Returns data source summaries and updates the system prompt
```class UpdateConversationSourcesRequest(BaseModel):
    source_ids: list[UUID] # list of active source ids
```
DELETE /api/v0/sources/{source_id}
- Handles deletion of a data source
- Deletes the data source and its summaries

My requirements are:
- simple no overkill to approach to updating the list of active data sources for a conversation. From the UI it will look like a single modal where user clicks on each data source. Then presses submit, which will send a request to the API.
- How do I handle therefore activation and deactivation of a data source? How to handle delete of a data source?

Data structure updates:
- Tables:
-- Mapping of conversation id and source id
-- Index on conversation id

```
-- Simple mapping table
CREATE TABLE conversation_sources (
    conversation_id UUID REFERENCES conversations(id),
    source_id UUID REFERENCES sources(id),
    PRIMARY KEY (conversation_id, source_id)
);

-- Source summaries table
CREATE TABLE source_summaries (
    source_id UUID PRIMARY KEY REFERENCES sources(id),
    summary TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Changes checklist [for you to update. List all tasks that I need to do to implement this]:
1. Implement the `generate_summary` task in Celery.
2. Create the `PUT /api/v0/conversations/{conversation_id}/sources` endpoint.
3. Create the `DELETE /api/v0/sources/{source_id}` endpoint.
4. Update the `ChatService` to handle fetching and updating conversation sources.
5. Update the database schema to include `conversation_sources` and `source_summaries` tables.
6. Ensure efficient batch loading of summaries when switching conversations.
7. Test the entire flow from source addition to summary generation and conversation updates.