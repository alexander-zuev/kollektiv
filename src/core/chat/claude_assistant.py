# TODO: Add user-specific session handling so multiple users can interact with the assistant concurrently.
# TODO: Implement async handling for document indexing, embedding, and summarizing to avoid blocking operations.
# TODO: Add a queue for managing multiple user requests (e.g., submitting multiple documents).
# TODO: Explore langgraph as a basis for the LLM chatbot with a RAG tool + persistence.L
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

import aiohttp
import weave
from anthropic import (
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    RateLimitError,
)
from anthropic.types import Message, MessageParam
from pydantic import BaseModel, ConfigDict, Field

from src.core._exceptions import (
    ClientDisconnectError,
    ConnectionError,
    StreamingError,
    TokenLimitError,
)
from src.core.chat.events import StandardEvent, StandardEventType
from src.core.decorators import anthropic_error_handler, base_error_handler
from src.core.search.vector_db import VectorDB
from src.infrastructure.config.settings import settings
from src.models.chat_models import (
    ConversationHistory,
    ConversationMessage,
    MessageContent,
    Role,
)

logger = logging.getLogger("kollektiv.src.core.chat.claude_assistant")

# Default system prompt for the assistant
DEFAULT_SYSTEM_PROMPT = """
You are an advanced AI assistant with access to various tools, including a powerful RAG (Retrieval
Augmented Generation) system. Your primary function is to provide accurate, relevant, and helpful
information to users by leveraging your broad knowledge base, analytical capabilities, and the specific
information available through the RAG tool.

Key guidelines:
1. Use RAG tool for queries requiring loaded documents or recent data
2. Analyze questions and context before using RAG
3. Formulate precise queries for relevant information
4. Integrate retrieved information with proper citations
5. Use general knowledge when RAG isn't relevant
6. Maintain accuracy and clarity
7. Be transparent about information sources
8. Express uncertainty when appropriate
9. Break down complex topics
10. Offer follow-up suggestions

Currently loaded document summaries:
{document_summaries}

Remember to use your tools judiciously and always prioritize providing accurate, helpful, and
contextually relevant information.
"""


class ClaudeAssistant(BaseModel):
    """Claude Assistant for chat interactions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Required attributes
    client: AsyncAnthropic | None = Field(default=None)
    vector_db: VectorDB
    retriever: Any = Field(default=None)  # Type will be specified in a future PR
    model_name: str = Field(default=settings.main_model)
    system_prompt: MessageContent = Field(
        default_factory=lambda: MessageContent.from_str(DEFAULT_SYSTEM_PROMPT),
        description="System prompt with document context"
    )
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)
    max_tokens: int = Field(default=4096)
    api_key: str = Field(default=settings.anthropic_api_key)
    retrieved_contexts: list[str] = Field(default_factory=list)

    def __init__(self, vector_db: VectorDB, **kwargs):
        """Initialize the Claude Assistant."""
        try:
            if weave and settings.weave_project_name:
                weave.init(settings.weave_project_name)
        except Exception as e:
            logger.warning(f"Failed to initialize weave: {str(e)}")

        # Initialize with all attributes
        super().__init__(
            vector_db=vector_db,
            **kwargs
        )

        # Initialize anthropic client after parent init
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            max_retries=2
        )

    async def update_system_prompt(self, document_summaries: list[dict[str, Any]] | None = None) -> None:
        """Update system prompt with document summaries."""
        if document_summaries:
            summaries_text = "\n".join(
                f"- {summary['filename']}: {summary['summary']}"
                for summary in document_summaries
            )
            new_prompt = DEFAULT_SYSTEM_PROMPT.format(document_summaries=summaries_text)
        else:
            new_prompt = DEFAULT_SYSTEM_PROMPT.format(document_summaries="No documents loaded.")

        self.system_prompt = MessageContent.from_str(new_prompt)

    async def stream_response(self, conversation: ConversationHistory) -> AsyncGenerator[StandardEvent, None]:
        """
        Stream a response from the assistant.

        Args:
            conversation: The conversation history to use for generating the response.

        Yields:
            StandardEvent: Events containing response content or error information.

        Raises:
            StreamingError: If there is an error during streaming.
            TokenLimitError: If the token limit is exceeded.
            ClientDisconnectError: If the client disconnects during streaming.
        """
        if not self.client:
            raise StreamingError("Anthropic client not initialized")

        try:
            messages = conversation.to_anthropic_messages()
            if not messages:
                raise ValueError("No messages in conversation history")

            # Add system prompt if it exists
            if self.system_prompt:
                messages.insert(0, {"role": "system", "content": self.system_prompt.to_anthropic()})

            stream = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                stream=True,
            )

            async for chunk in stream:
                if chunk.type == "message_start":
                    yield StandardEvent(
                        event_type=StandardEventType.MESSAGE_START,
                        content={"usage": chunk.usage}
                    )
                elif chunk.type == "content_block_start":
                    # Handle content block start if needed
                    continue
                elif chunk.type == "content_block_delta":
                    if chunk.delta.text:
                        yield StandardEvent(
                            event_type=StandardEventType.TEXT_TOKEN,
                            content=chunk.delta.text
                        )
                elif chunk.type == "message_delta":
                    # Handle message delta if needed
                    continue
                elif chunk.type == "message_stop":
                    yield StandardEvent(
                        event_type=StandardEventType.MESSAGE_STOP,
                        content={"usage": chunk.usage}
                    )

        except Exception as e:
            if isinstance(e, RateLimitError):
                raise TokenLimitError(f"Token limit exceeded: {str(e)}")
            elif isinstance(e, (APIStatusError, APITimeoutError)):
                raise StreamingError(f"API error during streaming: {str(e)}")
            elif isinstance(e, ClientDisconnectError):
                raise
            elif isinstance(e, (ConnectionError, aiohttp.ClientError)):
                raise StreamingError(f"Connection error during streaming: {str(e)}")
            else:
                raise StreamingError(f"Unexpected error during streaming: {str(e)}")

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = ConversationHistory()

    @base_error_handler
    async def _process_assistant_response(self, response: Message) -> str:
        """Process the assistant's response and update the conversation history."""
        logger.debug(
            f"Cached {response.usage.cache_creation_input_tokens} input tokens. \n"
            f"Read {response.usage.cache_read_input_tokens} tokens from cache"
        )
        # TODO: no longer needed?
        await self.conversation_history.add_message(role="assistant", content=response.content)
        await self.conversation_history.update_token_count(response.usage.input_tokens, response.usage.output_tokens)
        logger.debug(
            f"Processed assistant response. Updated conversation history: "
            f"{await self.conversation_history.get_conversation_history()}"
        )

        # Access the text from the first content block
        return response.content[0].text

    @base_error_handler
    async def handle_tool_use(self, tool_name: str, tool_input: dict[str, Any], tool_use_id: str) -> dict[str, Any]:
        """Handle tool use for specified tools."""
        try:
            if tool_name == "rag_search":
                search_results = await self.use_rag_search(tool_input=tool_input)
                tool_result = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Here is context retrieved by RAG search: \n\n{search_results}\n\n."
                            f"Please use this context to answer my original request, if it's relevant.",
                        }
                    ],
                }
                await self.conversation_history.add_message(**tool_result)
                logger.debug(
                    f"Debugging conversation history after tool use: "
                    f"{await self.conversation_history.get_conversation_history()}"
                )
                return tool_result

            raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"role": "system", "content": [{"type": "error", "content": f"Error: {str(e)}"}]}

    @anthropic_error_handler
    @weave.op()
    def formulate_rag_query(self, recent_conversation_history: list[dict[str, Any]], important_context: str) -> str:
        """
        Formulate a RAG search query based on recent conversation history and important context.

        Args:
            recent_conversation_history (list[dict[str, Any]]): A list of conversation history dictionaries.
            important_context (str): A string containing important contextual information.

        Returns:
            str: A formulated search query for RAG.

        Raises:
            ValueError: If 'recent_conversation_history' is empty.
        """
        logger.debug(f"Important context: {important_context}")

        if not recent_conversation_history:
            raise ValueError("Recent conversation history is empty")

        if not important_context:
            logger.warning("Important context is empty, proceeding to rag search query formulation without it")

        # extract most recent user query
        most_recent_user_query = next(
            (msg["content"] for msg in reversed(recent_conversation_history) if msg["role"] == "user"),
            "No recent " "user query found.",
        )

        query_generation_prompt = f"""
        Based on the following conversation context and the most recent user query, formulate the best possible search
        query for searching in the vector database.

        When preparing the query please take into account the following:
        - The query will be used to retrieve documents from a local vector database
        - The type of search used is vector similarity search
        - The most recent user query is especially important

        Query requirements:
        - Provide only the formulated query in your response, without any additional text.

        Recent conversation history:
        {recent_conversation_history}

        Important context to consider: {important_context}

        Most recent user query: {most_recent_user_query}

        Formulated search query:
        """

        system_prompt = (
            "You are an expert query formulator for a RAG system. Your task is to create optimal search "
            "queries that capture the essence of the user's inquiry while considering the full conversation context."
        )
        messages = [{"role": "user", "content": query_generation_prompt}]
        max_tokens = 150

        response = self.client.messages.create(
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            model=self.model_name,
        )

        rag_query = response.content[0].text.strip()
        return rag_query

    @base_error_handler
    def get_recent_context(self, n_messages: int = 6) -> list[dict[str, str]]:
        """
        Retrieve the most recent messages from the conversation history.

        Args:
            n_messages (int): The number of recent messages to retrieve. Defaults to 6.

        Returns:
            list[dict[str, str]]: A list of dictionaries representing the recent messages.

        Raises:
            None
        """
        recent_messages = self.conversation_history.messages[-n_messages:]
        return [msg.to_dict() for msg in recent_messages]

    @base_error_handler
    def use_rag_search(self, tool_input: dict[str, Any]) -> list[str]:
        """
        Perform a retrieval-augmented generation (RAG) search using the provided tool input.

        Args:
            tool_input (dict[str, Any]): A dictionary containing 'important_context' key to formulate the RAG query.

        Returns:
            list[str]: A list of preprocessed ranked documents resulting from the RAG search.

        Raises:
            KeyError: If 'important_context' is not found in tool_input.
        """
        # Get recent conversation context (last n messages for each role)
        recent_conversation_history = self.get_recent_context()

        # important context
        important_context = tool_input["important_context"]

        # prepare queries for search
        rag_query = self.formulate_rag_query(recent_conversation_history, important_context)
        logger.debug(f"Using this query for RAG search: {rag_query}")
        multiple_queries = self.generate_multi_query(rag_query)
        combined_queries = self.combine_queries(rag_query, multiple_queries)

        # get ranked search results
        results = self.retriever.retrieve(user_query=rag_query, combined_queries=combined_queries, top_n=3)
        logger.debug(f"Retriever results: {results}")

        # Preprocess the results here
        preprocessed_results = self.preprocess_ranked_documents(results)
        self.retrieved_contexts = preprocessed_results  # Store the contexts for evals
        logger.debug(f"Processed results: {results}")

        return preprocessed_results

    @base_error_handler
    def preprocess_ranked_documents(self, ranked_documents: dict[str, Any]) -> list[str]:
        """
        Preprocess ranked documents to generate a list of formatted document strings.

        Args:
            ranked_documents (dict[str, Any]): A dictionary where keys are document identifiers and values are
            dictionaries
            containing document details such as 'relevance_score' and 'text'.

        Returns:
            list[str]: A list of formatted document strings, each containing the document's relevance score and text.

        """
        preprocessed_context = []

        for _, result in ranked_documents.items():  # The first item (_) is the key, second (result) is the dictionary.
            relevance_score = result.get("relevance_score", None)
            text = result.get("text")

            # create a structured format
            formatted_document = (
                f"Document's relevance score: {relevance_score}: \n" f"Document text: {text}: \n" f"--------\n"
            )
            preprocessed_context.append(formatted_document)

        return preprocessed_context

    @anthropic_error_handler
    @weave.op()
    def generate_multi_query(self, query: str, model: str | None = None, n_queries: int = 5) -> list[str]:
        """
        Generate multiple related queries based on a user query.

        Args:
            query (str): The original user query.
            model (str, optional): The model used for generating queries. Defaults to None.
            n_queries (int, optional): The number of related queries to generate. Defaults to 5.

        Returns:
            list[str]: A list of generated queries related to the original query.

        Raises:
            Exception: If there is an error in the message generation process.
        """
        prompt = f"""
            You are an AI assistant whose task is to generate multiple queries as part of a RAG system.
            You are helping users retrieve relevant information from a vector database.
            For the given user question, formulate up to {n_queries} related, relevant questions to assist in
            finding the information.

            Requirements to follow:
            - Do NOT include any other text in your response except for 3 queries, each on a separate line.
            - Provide concise, single-topic questions (without compounding sentences) that cover various aspects of
            the topic.
            - Ensure each question is complete and directly related to the original inquiry.
            - List each question on a separate line without numbering.
            """
        if model is None:
            model = self.model_name

        message = self.client.messages.create(
            model=model,
            max_tokens=1024,
            system=prompt,
            messages=[{"role": "user", "content": query}],
        )

        content = message.content[0].text
        content = content.split("\n")
        return content

    @base_error_handler
    def combine_queries(self, user_query: str, generated_queries: list[str]) -> list[str]:
        """
        Combine user query with generated queries.

        Args:
            user_query (str): The initial user-provided query.
            generated_queries (list[str]): A list of queries generated by the system.

        Returns:
            list[str]: A list containing the user query and the filtered generated queries.

        Raises:
            None
        """
        combined_queries = [query for query in [user_query] + generated_queries if query.strip()]
        return combined_queries

    @anthropic_error_handler
    @weave.op()
    async def predict(self, question: str) -> dict:
        """
        Predict the answer to the given question.

        Args:
            question (str): The question for which an answer is to be predicted.

        Returns:
            dict: A dictionary containing the answer and the contexts retrieved.

        Raises:
            TypeError: If the `question` is not of type `str`.
            Exception: If there is an error in getting the response.
        """
        logger.debug(f"Predict method called with row: {question}")
        # user_input = row.get('question', '')

        self.reset_conversation()  # reset history and context for each prediction

        answer = self.get_response(question, stream=False)
        contexts = self.retrieved_contexts

        if contexts and len(contexts) > 0:
            context_snippet = contexts[0][:250]
            logger.info(f"Printing answer: {answer}\n\n " f"Based on the following contexts {context_snippet}")
        else:
            logger.warning("No contexts retrieved for the given model output")

        return {
            "answer": answer,
            "contexts": contexts,
        }

    # TODO: refactor to conversation history
    def reset_conversation(self) -> None:
        """
        Reset the conversation state to its initial state.

        Resets the conversation history and clears any retrieved contexts.

        Args:
            self: The instance of the class calling this method.

        Returns:
            None

        Raises:
            None
        """
        self.conversation_history = ConversationHistory()
        self.retrieved_contexts = []
