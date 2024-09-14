from typing import Dict, Any, List


class Tool:
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema
        }

class ToolManager:
    def __init__(self):
        self.tools: Dict[str, Any] = {}

    def add_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        return self.tools[name]

    def get_all_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self.tools.values()]


rag_search_tool = Tool(
    name='rag_search',
    description="""
    Retrieves relevant information from a local document database using RAG (Retrieval Augmented Generation).
    Use this tool when:
    1. The user asks about specific information that might be in the document database.
    2. You need to verify or expand on information related to the documents in the database.
    3. The query requires up-to-date or detailed information that might not be in your training data.
    
    To use effectively:
    1. Consider the user's question and recent conversation context.
    2. Formulate a clear, specific query that captures the essence of the information needed.
    3. Use the query to search the database and retrieve relevant document chunks.
    """,
    input_schema= {
        "type": "object",
            "properties": {
              "query": {
                "type": "string",
                "description": "A well-formulated search query based on the user's question and conversation context"
              }
            },
            "required": ["query"]
    }
)

tool_manager = ToolManager()
tool_manager.add_tool(
    rag_search_tool)