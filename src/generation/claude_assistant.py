import json
from pprint import pprint

from src.utils.logger import setup_logger
from src.utils.config import ANTHROPIC_API_KEY
from src.utils.decorators import error_handler
from typing import Dict, Any, List, Union
from src.generation.tool_definitions import ToolManager, tool_manager
from src.generation.query_generator import QueryGenerator

import anthropic

logger = setup_logger('claude_assistant', "claude_assistant.log")

# Client Class
class ClaudeAssistant:
    """
        ClaudeAssistant is an AI assistant class with a focus on providing accurate, relevant, and helpful information utilizing a Retrieval Augmented Generation (RAG) system.

        :param api_key: API key used for authenticating with the Claude API service.
        :param model_name: Name of the language model to be used.
    """
    def __init__(self, api_key :str =ANTHROPIC_API_KEY, model_name:str ="claude-3-5-sonnet-20240620"):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logger
        self.base_system_prompt = """
                You are an advanced AI assistant with access to various tools, including a powerful RAG (Retrieval Augmented Generation) system. Your primary function is to provide accurate, relevant, and helpful information to users by leveraging your broad knowledge base and the specific information available through the RAG tool.

                Key guidelines:
                1. Use the RAG tool when queries likely require information from loaded documents or recent data not in your training.
                2. Analyze the user's question and conversation context before deciding to use the RAG tool.
                3. When using RAG, formulate precise queries to retrieve the most relevant information.
                4. Seamlessly integrate retrieved information into your responses, citing sources when appropriate.
                5. If the RAG tool doesn't provide relevant information, rely on your general knowledge.
                6. Always strive for accuracy, clarity, and helpfulness in your responses.
                7. Be transparent about the source of your information (general knowledge vs. RAG-retrieved data).
                8. If you're unsure about information or if it's not in the loaded documents, say so honestly.

                Do not:
                - Invent or hallucinate information not present in your knowledge base or the RAG-retrieved data.
                - Use the RAG tool for general knowledge questions that don't require specific document retrieval.
                - Disclose sensitive details about the RAG system's implementation or the document loading process.

                Currently loaded document summaries:
                {document_summaries}

                Remember to use your tools judiciously and always prioritize providing the most accurate and helpful information to the user.
                """
        self.system_prompt = self.base_system_prompt.format(document_summaries="No documents loaded yet.")
        self.conversation_history: List[Dict[str, str]] = []
        self.tool_manager = tool_manager
        self.tools: List[Dict[str, Any]] = []
        self.retriever = None
        self.query_generator = QueryGenerator()

        self._init()


    @error_handler(logger)
    def _init(self):
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.tools = self.tool_manager.get_all_tools()  # Get all tools as a list of dicts

    @error_handler(logger)
    def update_system_prompt(self, document_summaries: List[Dict[str, Any]]):
        summaries_text = "\n".join(
            f"- {summary['summary']}"
            for summary in document_summaries
        )
        self.system_prompt = self.base_system_prompt.format(document_summaries=summaries_text)
        self.logger.debug(f"Updated system prompt: {self.system_prompt}")

    @error_handler(logger)
    def generate_response(self, user_input: str) -> str:
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            messages = self.conversation_history.copy()
            response = self.client.messages.create(
                messages=messages,
                system=self.system_prompt,
                max_tokens=8192,
                model=self.model_name,
                tools=self.tools
            )

            if response.stop_reason == "tool_use":
                assistant_message = []
                for content in response.content:
                    if content.type == 'text':
                        assistant_message.append({"type": "text", "text": content.text})
                    elif content.type == 'tool_use':
                        assistant_message.append({
                            "type": "tool_use",
                            "id": content.id,
                            "name": content.name,
                            "input": content.input
                        })

                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                for index, message in enumerate(self.conversation_history):
                    self.logger.debug(f"CONVERSATION HISTORY {index}: {message}")


                tool_results = []
                for content in response.content:
                    if content.type == 'text':
                    if content.type == 'tool_use':
                        tool_result = self.handle_tool_use(content, user_input)
                        self.logger.debug(f"Tool result: {tool_result}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": tool_result
                        })
                messages = self.conversation_history.copy()
                augmented_reply = self.get_augmented_response(user_input,
                                                              tool_results,
                                                              messages=messages)
                self.conversation_history.append({"role": "assistant", "content": augmented_reply})
                for index, message in enumerate(self.conversation_history):
                    self.logger.debug(f"CONVERSATION HISTORY {index}: {message}")

                return augmented_reply

            # If we're here, it's not a tool use response
            assistant_response = response.content[0].text
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            return assistant_response

        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return f"An error occurred: {str(e)}"



    @error_handler(logger)
    def handle_tool_use(self, tool_use_content: Dict[str, Any], user_input: str) -> Union[Dict[str, any], str]:
        tool_name = tool_use_content.name
        tool_input = tool_use_content.input

        try:
            # Execute the tool
            tool_result = self.call_tool(tool_name, tool_input, user_input)
            print(f"Printing type of the result: {type(tool_result)}")
            return {'content' : tool_result}
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error: {str(e)}"

    @error_handler(logger)
    def formulate_rag_query(self,
                            user_input: str,
                            recent_conversation_history: List[Dict[str, str]],
                            important_context: str) -> str:
        recent_conversation_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_conversation_history])

        if not recent_conversation_history:
            recent_conversation_history = "No conversation history yet, this might be the first message."

        query_generation_prompt = f"""
        Based on the following conversation context and the user's latest input, formulate the best possible search 
        query for retrieval augmented generation of information from local vector database.
        
        When preparing the query please take into account the following:
        - query will be used to retrieve the documents from a local vector database
        - type of search used: vector similarity search
        
        Query requirements:
        - Do not include any other text in your response, except for the query.

        Consider recent conversation history:
        {recent_conversation_history}

        Consider user's input itself: {user_input}

        Formulated search query:
        """

        self.logger.debug(f"Printing query generation prompt: {query_generation_prompt}")

        system_prompt = ("You are world's best query formulator for a RAG system. You know how to properly formulate search "
                         "queries that are relevant to the user's inquiry and take into account the recent conversation context.")
        messages = [{"role": "user", "content": query_generation_prompt}]
        max_tokens = 150

        response = self.client.messages.create(max_tokens=max_tokens,
                                            system=system_prompt,
                                            messages=messages,
                                            model=self.model_name,
                                            )

        return response.content[0].text.strip()

    @error_handler(logger)
    def get_recent_context(self, n_messages: int = 6) -> List[Dict[str, str]]:
        """Retrieves last 6 messages (3 user messages + 3 assistant messages)"""
        return self.conversation_history[-n_messages:]

    @error_handler(logger)
    def call_tool(self, tool_name: str,
                  tool_input: Dict[str, Any],
                  user_input: str) -> Dict[str, Any]:
        if tool_name == "rag_search":
            search_results = self.use_rag_search(user_input, tool_input)
            return search_results
        else:
            raise ValueError(f"Tool {tool_name} not supported")

    @error_handler(logger)
    def use_rag_search(self, user_input: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        # Get recent conversation context (last n messages for each role)
        recent_conversation_history = self.get_recent_context()

        # important context
        important_context = tool_input['important_context']

        # prepare queries for search
        rag_query = self.formulate_rag_query(user_input, recent_conversation_history, important_context)
        self.logger.debug(f"Using this query for RAG search: {rag_query}")
        multiple_queries = self.query_generator.generate_multi_query(rag_query)
        combined_queries = self.query_generator.combine_queries(rag_query, multiple_queries)

        # get search ranked search results
        results = self.retriever.retrieve(rag_query, combined_queries)
        return results


    @error_handler(logger)
    def update_conversation_history(self, user_input: str, assistant_response: str):
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

    @error_handler(logger)
    def generate_document_summary(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Aggregate metadata
        unique_urls = set(chunk['metadata']['source_url'] for chunk in chunks)
        unique_titles = set(chunk['metadata']['page_title'] for chunk in chunks)

        # Select diverse content samples
        sample_chunks = self._select_diverse_chunks(chunks, 5)
        content_samples = [chunk['data']['text'][:300] for chunk in sample_chunks]

        # Construct the summary prompt
        summary_prompt = f"""
        Generate a concise yet informative summary of the following documentation. Focus on key topics, themes, and the overall structure of the content.

        Document Metadata:
        - Unique URLs: {len(unique_urls)}
        - Unique Titles: {len(unique_titles)}

        Content Structure:
        {self._summarize_content_structure(chunks)}

        Content Samples:
        {self._format_content_samples(content_samples)}

        Instructions:
        1. Provide a 150-200 word summary that captures the essence of the documentation.
        2. Highlight the main topics or sections covered.
        3. Mention any notable features or key points that stand out.
        4. If applicable, briefly describe the type of documentation (e.g., API reference, user guide, etc.).
        5. Do not use phrases like "This documentation covers" or "This summary describes". Start directly with the key information.
        """

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=300,
            system="You are an expert at summarizing technical documentation concisely and accurately. Your summaries capture the essence of the content, making it easy for users to understand the scope and main topics of the documentation.",
            messages=[{"role": "user", "content": summary_prompt}]
        )

        summary = response.content[0].text

        return {
            'summary': summary,
        }

    def _select_diverse_chunks(self, chunks: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
        step = max(1, len(chunks) // n)
        return chunks[::step][:n]

    def _summarize_content_structure(self, chunks: List[Dict[str, Any]]) -> str:
        # Analyze the structure based on headers
        header_structure = {}
        for chunk in chunks:
            headers = chunk['data']['headers']
            for level, header in headers.items():
                if header:
                    header_structure.setdefault(level, set()).add(header)

        return "\n".join([f"{level}: {', '.join(headers)}" for level, headers in header_structure.items()])

    def _format_content_samples(self, samples: List[str]) -> str:
        return "\n\n".join(f"Sample {i + 1}:\n{sample}" for i, sample in enumerate(samples))


    @error_handler(logger)
    def preprocess_ranked_documents(self, ranked_documents: Dict[str, Any]) -> List[str]:
        """
        Converts ranked documents into a structured string for passing to the Claude API.
        """
        preprocessed_context = []

        for _, result in ranked_documents.items(): # The first item (_) is the key, second (result) is the dictionary.
            relevance_score = result.get('relevance_score', None)
            text = result.get('text')

            # create a structured format
            formatted_document = (
                f"Document's relevance score: {relevance_score}: \n"
                f"Document text: {text}: \n"
                f"--------\n"
            )
            preprocessed_context.append(formatted_document)

            # self.logger.info(f"Printing pre-chunks preprocessed_context {formatted_document}")

        return preprocessed_context

    @error_handler(logger)
    def get_augmented_response(self, user_input: str, tool_results: List[Dict[str, Any]], messages: List[Dict[str,
    str]]):

        # process context
        preprocessed_context = self.preprocess_ranked_documents(tool_results[0]['content']['content'])

        # Create a new user message with tool results
        new_message = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_results[0]['tool_use_id'],  # Assuming the tool_use_id is in the tool_results
                    "content": f"Here is context retrieved by a RAG system: \n\n{preprocessed_context}\n\n."
                                      f"Respond to the latest user's query using the provided context."
                                      f"User_input: {user_input}"
                }
            ]
        }
        # Create a new list with the existing messages and the new message
        updated_messages = messages + [new_message]
        self.conversation_history.append(new_message)
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                system=self.system_prompt,
                messages=updated_messages,
                tools=self.tools
            )
            content = response.content[0].text
        except Exception as e:
            self.logger.error(f"Exception while processing Anthropic response: {e}")
            raise

        return content