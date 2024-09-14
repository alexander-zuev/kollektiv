import json

from src.utils.logger import setup_logger
from src.utils.config import ANTHROPIC_API_KEY
from src.utils.decorators import error_handler
from typing import Dict, Any, List
from src.generation.tool_definitions import ToolManager, tool_manager
from src.generation.query_generator import QueryGenerator

import anthropic

logger = setup_logger('claude_assistant', "claude_assistant.log")

# Client Class
class ClaudeAssistant:
    def __init__(self, api_key :str =ANTHROPIC_API_KEY, model_name:str ="claude-3-5-sonnet-20240620"):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logger
        self.system_prompt = """
                You are an AI assistant with access to a RAG (Retrieval Augmented Generation) tool.
                Use the RAG tool when you need to retrieve specific information from the document database.
                Consider the user's question and recent conversation context when deciding to use the RAG tool.
                If you use the RAG tool, formulate a clear and specific query to get the most relevant information.
                After using the RAG tool, incorporate the retrieved information into your response, citing the source when appropriate.
                If the RAG tool doesn't provide relevant information, rely on your general knowledge to answer the query.
                """
        self.conversation_history: List[Dict[str, str]] = []
        self.tool_manager = tool_manager  # Use the pre-initialized tool_manager
        self.tools: List[Dict[str, Any]] = []  # Initialize as an empty list
        self.retriever = None
        self.query_generator = QueryGenerator()

        self._init()


    @error_handler(logger)
    def _init(self):
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.tools = self.tool_manager.get_all_tools()  # Get all tools as a list of dicts
        self.logger.info("Successfully initialized Anthropic client")


    @error_handler(logger)
    def generate_response(self, user_input: str) -> str:

        messages = self.conversation_history + [{"role": "user", "content": user_input}]

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=8192,
            system=self.system_prompt,
            messages=messages,
            tools=self.tool_manager.get_all_tools()
        )

        # check for tool use
        if response.stop_reason == "tool_use":
            for content in response.content:
                if content.type == 'tool_use' and content.name == 'rag_search':
                    # Formulate the best possible query using recent context
                    tool_result = self.call_tool(content.name, content.input, user_input)
                    messages.append({
                        'role': 'user',
                        'content': [{
                            'type': 'tool_result',
                            'tool_use_id': content.id,
                            'content': tool_result
                        }]
                    })

            final_response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                system=self.system_prompt,
                messages=messages,
            )
            assistant_response = final_response.content[0].text
            self.update_conversation_history(user_input, assistant_response)
        else:
            assistant_response = response.content[0].text
            self.update_conversation_history(user_input, assistant_response)
            return assistant_response

    @error_handler(logger)
    def formulate_rag_query(self, user_input: str, recent_context: List[Dict[str, str]]) -> str:
        context_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_context])

        query_generation_prompt = f"""
        Based on the following conversation context and the user's latest input, formulate the best possible search 
        query for retrieving relevant information using RAG from a local vector database.
        
        Query requirements:
        - Do not include any other text in your response, except for the query.

        Recent conversation context:
        {context_prompt}

        User's latest input: {user_input}

        Formulated search query:
        """

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=150,
            system="You are world's best query formulator for a RAG system. You know how to properly formulate search "
                   "queries that are relevant to the user's inquiry and take into account the recent conversation context.",
            messages=[{"role": "user", "content": query_generation_prompt}]
        )

        return response.content[0].text.strip()

    @error_handler(logger)
    def get_recent_context(self, n_messages: int = 6) -> List[Dict[str, str]]:
        """Retrieves last 6 messages (3 user messages + 3 assistant messages)"""
        return self.conversation_history[-n_messages:]

    @error_handler(logger)
    def call_tool(self, tool_name: str,
                  tool_input: Dict[str, Any],
                  user_input: str) -> str:
        if tool_name == "rag_search":
            search_results = self.use_rag_search(user_input)
            return json.dumps(search_results)  # Convert results to a string for passing back to Claude
        else:
            raise ValueError(f"Tool {tool_name} not supported")

    @error_handler(logger)
    def use_rag_search(self, user_input: str) -> str:
        # Get recent conversation context (last 3 messages)
        recent_context = self.get_recent_context()

        # prepare queries for search
        rag_query = self.formulate_rag_query(user_input, recent_context)
        multiple_queries = self.query_generator.generate_multi_query(rag_query)
        combined_queries = self.query_generator.combine_queries(rag_query, multiple_queries)

        # get search ranked search results
        results = self.retriever.retrieve(rag_query, combined_queries)
        return json.dumps(results)


    @error_handler(logger)
    def update_conversation_history(self, user_input: str, assistant_response: str):
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

    @error_handler(logger)
    def preprocess_ranked_documents(self, ranked_documents: Dict[str, Any]) -> List[str]:
        """
        Converts ranked documents into a structured string for passing to the Claude API.
        """
        preprocessed_context = []

        for _, result in ranked_documents.items(): # The first item (_) is the key, second (result) is the dictionary.
            relevance_score = result.get('relevance_score')
            text = result.get('text')

            # create a structured format
            formatted_document = (
                f"Document's relevance score: {relevance_score}: \n"
                f"Document text: {text}: \n"
                f"--------\n"
            )
            preprocessed_context.append(formatted_document)

            # self.logger.debug(f"Printing pre-chunks preprocessed_context {formatted_document}")

        return preprocessed_context

    @error_handler(logger)
    def get_augmented_response(self, user_query: str, context: Dict[str, Any], model_name: str =
    "claude-3-5-sonnet-20240620"):

        # process context
        preprocessed_context = self.preprocess_ranked_documents(context)

        system_prompt = (
            f"You are a knowledgable financial research assistant. Your users are inquiring about an annual report."
            f"You will be given context, extracted by an LLM that will help in answering the "
            f"questions. Each context has a relevance score and the document itself"
            f"If the provided context is not relevant, please inform the user that you can not "
            f"answer the question based on the provided information."
            f"If the provided context is relevant, answer the question based on the contex")

        messages = [
            {"role": "user", "content": f"Context: \n\n{preprocessed_context}\n\n."
                                    f"Answer the questions based on the provided context."
                                    f"Question: {user_query}"},

        ]

        try:
            response = self.client.messages.create(
                model=model_name,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
            )
            content = response.content[0].text
            self.logger.debug("Received response from Anthropic")
        except Exception as e:
            self.logger.error(f"Exception while processing Anthropic response: {e}")
            raise

        return content



def main():
    ca = ClaudeAssistant()

    user_input = input("What do you want to chat about? ")
    while user_input != "exit":
        response = ca.generate_response(user_input)
        print(response)

if __name__ == "__main__":
    main()