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
    
    When to use this tool:
    1. The user request / input requires up to date information about libraries that are indexed in the local vector 
    database.
    2. The user's request can be validated by the information that you have in the database.
    3. You need to verify or expand on information related to the documents in the database.
    
    How to use this tool effectively:
    1. Start by analyzing and understanding the conversation context
    2. Then analyze the most recent user request
    3. Then define what is the most important context that should be taken into account by the LLM assistant that is 
    formulating the actual search query. Keep in mind that the search query is going to be used for RAG search, 
    based on vector similarity.
    
    How this tool results are going to be used:
    - You call the tool_use, if necessary
    - Another method is formulating the best rag query based on your input, recent conversation history
    - RAG search and retrieval is performed

    """,
    input_schema= {
        "type": "object",
            "properties": {
              "important_context": {
                "type": "string",
                "description": "The most important context that should be taken into account by the LLM assistant "
                               "that is going to be generating the actual search query."
              }
            },
            "required": ["important_context"]
    }
)

tool_manager = ToolManager()
tool_manager.add_tool(
    rag_search_tool)