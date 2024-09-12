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
2. No validation of chunking result
   - No basic checks for preservation of h1 and h2 and h3 headers 
   - No basic checks for content volume preservation 
3. No (basic) evals setup for the RAG app with at least F1, precision, recall metrics
4. No support for LLM chat with RAG tools

# Scope
- Fix the problem statements above so that I am closer to the initial release state

# Approach
- Analytically define problems with chunking
- Identify ways to resolve the issues
- Resolve and test

# Success Metrics
- Chunking validation metrics should be reported for each chunked file
- RAG evals should be done for a set of questions based on parsed docs

# Implementation
## Details