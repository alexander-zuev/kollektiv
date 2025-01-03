
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
- A source becomes "active"
- At this point summary should be added and saved to the LLM assistant
- Summary can be persisted to supabase for simplicity (no Redis cache)
- For simplicity, adding or removing a source should trigger incremental summary updates (loading / unloading)
- If you proove that I can very simply use Redis cache, then I can use it in addition to Supabase, but I fear for the need to syncronize the state. Although it should be easy to do.

Questions to you:
- Do you think this appraoch makes sense?
- How else in RAG systems this problem is solved?
- How else do RAG systems solve the problem of LLMs not knowing what sources are available? They need to know when to query and when not to query.

Lifecycle:
- Activation of a data source
-- Data source is either added by users or activated by users in the UI
-- Each conversation will have a mapping of data sources that are active for that conversation
-- When a user loads a conversation, a Conversation object holds the list of IDs of data sources that are active for that conversation
-- At this point, the summary is retrieved from Supabase, and added to the system prompt
-- System prompt limit for:
--- Anthropic
--- OpenAI
--- Gooogle

- Switching between conversations
-- When a user switches between conversations, the Conversation object is updated with the new list of active data sources
- Deactivating of a data source
-- When a user deselects a data source, FE sends an awaitable request that removes the ID of tha data source and retrieves and updates the loaded summaries.

Key constraints:
- Switching between conversations should necessarily involve loading of summaries into the prompt. How to ensure this is super fast?