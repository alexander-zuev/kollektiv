from typing import Any


class Tool:
    """
    Represent a tool with a name, description, and input schema.

    Args:
        name (str): The name of the tool.
        description (str): A brief description of the tool.
        input_schema (dict[str, Any]): A dictionary representing the input schema of the tool.
    """

    def __init__(self, name: str, description: str, input_schema: dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


class ToolManager:
    """
    Manage a collection of tools.

    Args:
        None

    Attributes:
        tools (dict[str, Any]): A dictionary storing tools with their name as the key.
    """

    def __init__(self):
        self.tools: dict[str, Any] = {}

    def add_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        return self.tools[name]

    def get_all_tools(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self.tools.values()]


rag_search_tool = Tool(
    name="rag_search",
    description="""
        Retrieves relevant information from a local document database using RAG (Retrieval Augmented Generation)
        technology. This tool performs a semantic search on a vector database containing pre-processed and embedded
        documents, returning the most relevant content based on the input query.

        What this tool does:
        1. Analyzes the conversation context and user query to formulate an optimal search query.
        2. Performs a vector similarity search in the local document database.
        3. Retrieves and ranks the most relevant document chunks.
        4. Returns a list of relevant text passages along with their relevance scores.

        When to use this tool:
        1. The user request requires up-to-date information about specific libraries, APIs, or topics that are indexed
        in the local vector database.
        2. You need to verify or expand on information related to the documents in the database.
        3. The user's query is complex or requires detailed technical information that may not be part of your general
        knowledge.
        4. You need to provide accurate, source-based responses for technical or domain-specific questions.

        When NOT to use this tool:
        1. For general knowledge questions that don't require specific document retrieval.
        2. When the user's query is clearly outside the scope of the indexed documents.
        3. For tasks that require real-time data or information that wouldn't be present in static documentation.

        Parameters:
        - important_context (string, required): The key information from the conversation history and current query
        that should be considered when formulating the search query. This helps in generating a more targeted and
        relevant search.

        How this tool's results are used:
        1. The tool returns a list of relevant text passages and their relevance scores.
        2. You should analyze these passages and incorporate the most relevant information into your response.
        3. Always cite or reference the source of the information when using it in your answers.

        Important caveats and limitations:
        1. The tool's effectiveness depends on the quality and recency of the indexed documents.
        2. It may not have information on very recent developments or changes not yet indexed in the database.
        3. The tool does not understand or interpret the retrieved information; it's your responsibility to analyze and
        use it appropriately.
        4. The relevance scores are based on vector similarity and may not always perfectly match semantic relevance.
        5. This tool does not have access to external resources or the internet; it only searches the local
        document database.

        Remember to use this tool judiciously and always prioritize providing accurate, helpful, and contextually
        relevant information to the user.
        """,
    input_schema={
        "type": "object",
        "properties": {
            "important_context": {
                "type": "string",
                "description": "The most important context that should be taken into account by the LLM assistant "
                "that is going to be generating the actual search query.",
            }
        },
        "required": ["important_context"],
    },
)

tool_manager = ToolManager()
tool_manager.add_tool(rag_search_tool)
