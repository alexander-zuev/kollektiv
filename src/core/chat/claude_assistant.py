# TODO: Add user-specific session handling so multiple users can interact with the assistant concurrently.
# TODO: Implement async handling for document indexing, embedding, and summarizing to avoid blocking operations.
# TODO: Add a queue for managing multiple user requests (e.g., submitting multiple documents).
# TODO: Explore langgraph as a basis for the LLM chatbot with a RAG tool + persistence.L
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import anthropic
import weave
from pydantic import ConfigDict, Field
from weave import Model

from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.tool_definitions import tool_manager
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.decorators import anthropic_error_handler, base_error_handler
from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings
from src.models.chat_models import ConversationHistory, MessageContent, StandardEvent, StandardEventType

logger = get_logger()


class ClaudeAssistant(Model):
    """
    Define the ClaudeAssistant class for managing AI assistant functionalities with various tools and configurations.

    Args:
        vector_db (VectorDB): The vector database instance for retrieving contextual information.
        api_key (str, optional): The API key for the Anthropic client. Defaults to ANTHROPIC_API_KEY.
        model_name (str, optional): The name of the model to use. Defaults to MAIN_MODEL.

    Raises:
        anthropic.exceptions.AnthropicError: If there's an error initializing the Anthropic client.

    Methods:
        _init: Initialize the assistant's client and tools.
        update_system_prompt: Update the system prompt with document summaries.
        cached_system_prompt: Get the cached system prompt as a list.
        cached_tools: Get the cached tools as a list.
        preprocess_user_input: Preprocess the user input to remove whitespace and newlines.
        get_response: Generate a response based on user input, either as a stream or a single string.
        stream_response: Handle the streaming response from the assistant and manage conversation flow.

    """

    client: anthropic.AsyncAnthropic | None = None
    vector_db: VectorDB
    api_key: str | None = Field(default=settings.anthropic_api_key)
    model_name: str = Field(default=settings.main_model)
    base_system_prompt: str = Field(default="")
    system_prompt: str = Field(default="")
    # TODO: no longer needed?
    conversation_history: ConversationHistory | None = None
    retrieved_contexts: list[str] = Field(default_factory=list)
    tool_manager: Any = Field(default_factory=lambda: tool_manager)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    extra_headers: dict[str, str] = Field(default_factory=lambda: {"anthropic-beta": "prompt-caching-2024-07-31"})
    retriever: Any | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        vector_db: VectorDB,
        api_key: str | None = None,
        model_name: str | None = None,
    ):
        # Initialize weave only if project name is set and non-empty
        if settings.weave_project_name and settings.weave_project_name.strip():
            try:
                weave.init(settings.weave_project_name)
            except Exception as e:
                logger.warning(f"Failed to initialize weave: {e}")

        # Initialize fields via super().__init__()
        super().__init__(
            client=None,
            vector_db=vector_db,
            api_key=api_key or settings.anthropic_api_key,
            model_name=model_name or settings.main_model,
            base_system_prompt="""
                    You are an advanced AI assistant with access to various tools, including a powerful RAG (Retrieval
                    Augmented Generation) system. Your primary function is to provide accurate, relevant, and helpful
                    information to users by leveraging your broad knowledge base, analytical capabilities,
                    and the specific information available
                    through the RAG tool.
                    Key guidelines:

                    Use the RAG tool when queries likely require information from loaded documents or recent data not
                    in your training.
                    Carefully analyze the user's question and conversation context before deciding whether to use the
                    RAG tool.
                    When using RAG, formulate precise and targeted queries to retrieve the most relevant information.
                    Seamlessly integrate retrieved information into your responses, citing sources when appropriate.
                    If the RAG tool doesn't provide relevant information, rely on your general knowledge and analytical
                    skills.
                    Always strive for accuracy, clarity, and helpfulness in your responses.
                    Be transparent about the source of your information (general knowledge vs. RAG-retrieved data).
                    If you're unsure about information or if it's not in the loaded documents, clearly state your
                     uncertainty.
                    Provide context and explanations for complex topics, breaking them down into understandable parts.
                    Offer follow-up questions or suggestions to guide the user towards more comprehensive understanding.

                    Do not:

                    Invent or hallucinate information not present in your knowledge base or the RAG-retrieved data.
                    Use the RAG tool for general knowledge questions that don't require specific document retrieval.
                    Disclose sensitive details about the RAG system's implementation or the document loading process.
                    Provide personal opinions or biases; stick to factual information from your knowledge base and
                    RAG system.
                    Engage in or encourage any illegal, unethical, or harmful activities.
                    Share personal information about users or any confidential data that may be in the loaded documents.

                    Currently loaded document summaries:
                    {document_summaries}
                    Use these summaries to guide your use of the RAG tool and to provide context for the types of
                     questions
                    you can answer with the loaded documents.
                    Interaction Style:

                    Maintain a professional, friendly, and patient demeanor.
                    Tailor your language and explanations to the user's apparent level of expertise.
                    Ask for clarification when the user's query is ambiguous or lacks necessary details.

                    Handling Complex Queries:

                    For multi-part questions, address each part systematically.
                    If a query requires multiple steps or a lengthy explanation, outline your approach before diving
                    into details.
                    Offer to break down complex topics into smaller, more manageable segments if needed.

                    Continuous Improvement:

                    Learn from user interactions to improve your query formulation for the RAG tool.
                    Adapt your response style based on user feedback and follow-up questions.

                    Remember to use your tools judiciously and always prioritize providing the most accurate,
                    helpful, and contextually relevant information to the user. Adapt your communication style to
                    the user's level of understanding and the complexity of the topic at hand.
                    """,
            system_prompt="",  # Will format below
            # TODO: no longer needed?
            conversation_history=None,  # Will initialize in _init()
            retrieved_contexts=[],
            tool_manager=tool_manager,
            tools=[],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            retriever=None,
        )
        # Set the formatted system prompt
        self.system_prompt = self.base_system_prompt.format(document_summaries="No documents loaded yet.")
        # Initialize client and conversation history
        self._init()

    @anthropic_error_handler
    def _init(self) -> None:
        """Initialize the Claude Assistant with API client and tools."""
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key, max_retries=2)
        # TODO: no longer needed?
        self.conversation_history = ConversationHistory()
        self.tools = self.tool_manager.get_all_tools()
        logger.debug("Claude assistant successfully initialized.")

    @base_error_handler
    async def update_system_prompt(self, document_summaries: list[dict[str, Any]]) -> None:
        """Update the system prompt with document summaries."""
        logger.info(f"Loading {len(document_summaries)} summaries")
        summaries_text = "\n\n".join(
            f"* file: {summary['filename']}:\n"
            f"* summary: {summary['summary']}\n"
            f"* keywords: {', '.join(summary['keywords'])}\n"
            for summary in document_summaries
        )
        self.system_prompt = self.base_system_prompt.format(document_summaries=summaries_text)
        logger.debug(f"Updated system prompt: {self.system_prompt}")

    @base_error_handler
    async def cached_system_prompt(self) -> list[dict[str, Any]]:
        """Retrieve the cached system prompt."""
        return [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}]

    @base_error_handler
    async def cached_tools(self) -> list[dict[str, Any]]:
        """Return a list of cached tools with specific attributes."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
                "cache_control": {"type": "ephemeral"},
            }
            for tool in self.tools
        ]

    @base_error_handler
    async def preprocess_user_input(self, input_text: str) -> str:
        """
        Preprocess user input by removing whitespace and replacing newlines.

        Args:
            input_text (str): The user input text to preprocess.

        Returns:
            str: The preprocessed user input with no leading/trailing whitespace and newlines replaced by spaces.
        """
        # Remove any leading/trailing whitespace
        cleaned_input = input_text.strip()
        # Replace newlines with spaces
        cleaned_input = " ".join(cleaned_input.split())
        return cleaned_input

    @anthropic_error_handler
    async def stream_response(self, conv_history: ConversationHistory) -> AsyncGenerator[StandardEvent, None]:
        """Stream responses from a conversation, handle tool use, and process assistant replies."""
        try:
            logger.debug(f"Conversation history: {len(conv_history.messages)} messages.")

            while True:
                messages = conv_history.to_anthropic_messages()
                logger.debug(f"Messages: {messages}")
                async with self.client.messages.stream(
                    messages=messages,
                    system=await self.cached_system_prompt(),
                    max_tokens=8192,
                    model=self.model_name,
                    tools=await self.cached_tools(),
                    extra_headers=self.extra_headers,
                ) as stream:
                    async for event in stream:
                        logger.debug(f"Received event type: {event.type}")

                        # Match conditions
                        match event.type:
                            case "message_start":
                                logger.debug("===== Stream message started =====")
                                yield StandardEvent(event_type=StandardEventType.MESSAGE_START, content="")
                            case "text":
                                logger.debug(f"===== Stream text token: {event.text} =====")
                                yield StandardEvent(event_type=StandardEventType.TEXT_TOKEN, content=event.text)

                            case "content_block_start":
                                logger.debug("===== Stream content block started =====")
                                if event.content_block.type == "tool_use":
                                    yield StandardEvent(
                                        event_type=StandardEventType.TOOL_START,
                                        content={
                                            "type": "tool_use",
                                            "tool": event.content_block.name,
                                        },
                                    )
                            case "content_block_stop":
                                logger.debug("===== Stream content block ended =====")
                            case "message_stop":
                                logger.debug("===== Stream message ended =====")
                                yield StandardEvent(event_type=StandardEventType.MESSAGE_STOP, content="")
                            case "error":
                                logger.error(f"===== Stream error: {event.error} =====")
                                # TODO: handle error -> raise

                    # Get final message
                    full_response = await stream.get_final_message()
                    logger.debug(f"Full response: {full_response}")
                    yield StandardEvent(
                        event_type=StandardEventType.FULL_MESSAGE, content=MessageContent(blocks=full_response.content)
                    )
                    # logger.debug(f"Final message: {assistant_response}")
                    # await self._process_assistant_response(assistant_response)

                    # Handle tool use and get results
                    tool_use_block = next((block for block in full_response.content if block.type == "tool_use"), None)
                    if tool_use_block:
                        tool_result = await self.handle_tool_use(
                            tool_use_block.name, tool_use_block.input, tool_use_block.id
                        )
                        yield StandardEvent(
                            event_type=StandardEventType.TOOL_RESULT, content=MessageContent(blocks=tool_result)
                        )
                        logger.debug(f"Tool result: {StandardEvent.content}")
                    if not tool_use_block:
                        break
        except (RetryableLLMError, NonRetryableLLMError) as e:
            logger.error(f"An error occured in stream response: {str(e)}", exc_info=True)
            raise

    # @base_error_handler
    # async def _process_assistant_response(self, response: PromptCachingBetaMessage | Message) -> str:
    #     """Process the assistant's response and update the conversation history."""
    #     logger.debug(
    #         f"Cached {response.usage.cache_creation_input_tokens} input tokens. \n"
    #         f"Read {response.usage.cache_read_input_tokens} tokens from cache"
    #     )
    #     # TODO: no longer needed?
    #     await self.conversation_history.add_message(role="assistant", content=response.content)
    #     await self.conversation_history.update_token_count(response.usage.input_tokens, response.usage.output_tokens)
    #     logger.debug(
    #         f"Processed assistant response. Updated conversation history: "
    #         f"{await self.conversation_history.get_conversation_history()}"
    #     )

    #     # Access the text from the first content block
    #     return response.content[0].text

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
