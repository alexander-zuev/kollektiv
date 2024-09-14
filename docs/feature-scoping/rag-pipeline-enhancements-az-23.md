# Description
I am at a state that RAG pipeline works end to end, however there are several important limitations in the current 
implementation that I'd want to address before calling it a v0.1 release.

**Current state for context:**
- user can parse multiple URLs using FireCrawl
- user can chunk the results, only in markdown format
- chunking is brittle and not ideal or close to sufficient IMO - probably requires the most work
- user can create a local persistent chroma db
- user can directly query db
- user can NOT chat with LLM and it automatically decides when to query db
- llm client doesn't have tools to automatically call the vector db when needed
- llm client doesn't recognize user commands to load more documents if necessary

# Problem statements
1. Improve chunking quality and stability further for markdown docs only
    - Define a clear list of problems based on parsing top 3 libraries I work with
    - Define a MECE, flexible chunking approach
2. No validation of chunking result - COMPLETED
   - No basic checks for preservation of h1 and h2 and h3 headers 
   - No basic checks for content volume preservation 
3. No (basic) evals setup for the RAG app with at least F1, precision, recall metrics
4. No support for LLM chat with RAG tools

## Identified problems with chunking


# Scope
1. Fix identified chunking issues
2. Setup basic RAG evaluation suite
3. Implement flow orchestrator
   - Sonnet 3.5 
   - Tool definition
      - RAG
   - Intelligent decision-making for when to use RAG
4. Re-factor and simplify implementation
5. Implement chainlit for basic UI
6. Create a live demo using Supabase or Anthropic docs
7. Create a user guide (md) on how to use key modules and limitations
8. Create an in-depth video on how to use RAGDocs over your own data

# Success Metrics
1. Chunking
   - % of headers preserved -> 100%
   - % of tokens preserved -> 100% or close enough, but it will never be 1:1 due to pre-processing
2. RAG evals
   - Avg Precision, Recall, F1, MRR 