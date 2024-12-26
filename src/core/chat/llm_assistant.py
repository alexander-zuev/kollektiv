from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterable
from typing import Any

import anthropic
import weave
from anthropic import AsyncStream
from anthropic.types import (
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    InputJSONDelta,
    Message,
    MessageParam,
    RawContentBlockDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextBlockParam,
    TextDelta,
    ToolParam,
)
from anthropic.types.message_stream_event import MessageStreamEvent
from pydantic import ConfigDict, Field
from weave import Model

from src.core._exceptions import NonRetryableLLMError, RetryableLLMError
from src.core.chat.prompt_manager import PromptManager
from src.core.chat.tool_manager import ToolManager
from src.core.search.retriever import Retriever
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.decorators import (
    anthropic_error_handler,
    base_error_handler,
)
from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings
from src.models.chat_models import (
    AssistantMessageEvent,
    ConversationHistory,
    ErrorEvent,
    StreamingEvent,
    StreamingEventType,
    StreamingTextDelta,
    TextBlock,
    ToolResultBlock,
    ToolResultEvent,
    ToolUseBlock,
)
from src.models.llm_models import SystemPrompt, Tool, ToolName

logger = get_logger()


class ClaudeAssistant(Model):
    """
    Define the ClaudeAssistant class for managing AI assistant functionalities with various tools and configurations.

    Args:
        vector_db (VectorDB): The vector database instance for retrieving contextual information.
        retriever (Retriever): The retriever instance for RAG operations.
        api_key (str, optional): The API key for the Anthropic client. Defaults to ANTHROPIC_API_KEY.
        model_name (str, optional): The name of the model to use. Defaults to MAIN_MODEL.

    Raises:
        anthropic.exceptions.AnthropicError: If there's an error initializing the Anthropic client.
        NonRetryableLLMError: If there's an error initializing dependencies.
    """

    # Required fields
    vector_db: VectorDB

    # Client config
    client: anthropic.AsyncAnthropic | None = Field(default=None)
    extra_headers: dict[str, str] = Field(default_factory=lambda: {"anthropic-beta": "prompt-caching-2024-07-31"})
    api_key: str = Field(default=settings.anthropic_api_key)
    model_name: str = Field(default=settings.main_model)
    system_prompt: SystemPrompt = Field(default_factory=lambda: SystemPrompt(text=""))
    tools: list[Tool] = Field(default_factory=list, description="List of tools available to the assistant")

    # Dependencies
    prompt_manager: PromptManager = Field(default_factory=PromptManager)
    tool_manager: ToolManager = Field(default_factory=ToolManager)
    retriever: Retriever | None = Field(default=None, description="Retriever instance")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        vector_db: VectorDB,
        retriever: Retriever,
        api_key: str | None = None,
        model_name: str | None = None,
    ):
        # Initialize weave if configured
        if settings.weave_project_name and settings.weave_project_name.strip():
            try:
                weave.init(settings.weave_project_name)
            except Exception as e:
                logger.warning(f"Failed to initialize weave: {e}")

        # Initialize Pydantic model with required fields
        super().__init__(
            vector_db=vector_db,
            api_key=api_key or settings.anthropic_api_key,
            model_name=model_name or settings.main_model,
        )

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key, max_retries=2)
        self.tools = [self.tool_manager.get_tool(ToolName.RAG_SEARCH)]
        self.system_prompt = self.prompt_manager.get_system_prompt(document_summaries="No documents loaded yet.")
        self.retriever = retriever
        logger.info("✓ Initialized Claude assistant successfully")

    # TODO: this method needs to be refactored completely
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
        self.system_prompt = self.prompt_manager.get_system_prompt(document_summaries=summaries_text)
        logger.debug(f"Updated system prompt: {self.system_prompt}")

    @property
    def cached_system_prompt(self) -> list[TextBlockParam]:
        """Get cached system prompt for Anthropic API."""
        return [self.system_prompt.with_cache()]

    @property
    def cached_tools(self) -> Iterable[ToolParam]:
        """Return a list of cached tools with specific attributes."""
        return [tool.with_cache() for tool in self.tools]

    @anthropic_error_handler
    async def stream_response(self, conv_history: ConversationHistory) -> AsyncGenerator[StreamingEvent, None]:
        """Stream responses from a conversation, handle tool use, and process assistant replies."""
        try:
            logger.debug(f"Number of messages in conversation history: {len(conv_history.messages)}")

            max_retries = 2
            retries = 0
            current_tool_use_block: ToolUseBlock | None = (
                None  # used to track if we have content block of type tool_use
            )
            tool_input_json = ""  # to accumulate tool use
            tool_result = None
            message_stop_event = None

            while retries < max_retries:
                messages = conv_history.to_anthropic_messages()
                logger.debug(f"Debugging messages list for Anthropic API: {messages}")
                async with self.client.messages.stream(
                    messages=messages,
                    system=self.cached_system_prompt,
                    max_tokens=8192,
                    model=self.model_name,
                    tools=self.cached_tools,
                    extra_headers=self.extra_headers,
                ) as stream:
                    async for event in stream:
                        # Match event type
                        match event.type:
                            case "message_start":
                                yield self.handle_message_start(event)  # type: ignore
                            case "content_block_start":
                                current_tool_use_block = self.handle_content_block_start(event)  # type: ignore
                            case "content_block_delta":
                                result = self.handle_content_block_delta(event, tool_input_json)  # type: ignore
                                event, tool_input_json = result
                                if event:
                                    yield event
                            case "content_block_stop":
                                if event.content_block.type == "tool_use" and current_tool_use_block:  # type: ignore
                                    tool_result = await self.handle_content_block_stop(
                                        event,
                                        current_tool_use_block,
                                        tool_input_json,  # type: ignore
                                    )
                                    continue
                            case "message_stop":
                                message_stop_event = self.handle_message_stop(event)  # type: ignore
                            case "error":
                                yield self.handle_error(event)  # type: ignore

                    # Get final message
                    assistant_response = await self.handle_full_message(stream)  # type: ignore
                    yield assistant_response
                    logger.debug(f" EVENT RESPONSE FOR DEBUGGING: {assistant_response}")

                    # If tool result, yield tool result
                    if tool_result:
                        yield StreamingEvent(
                            event_type=StreamingEventType.TOOL_RESULT,
                            event_data=ToolResultEvent(
                                content=tool_result,
                            ),
                        )
                    # Finally
                    if message_stop_event:
                        yield message_stop_event

        except (RetryableLLMError, NonRetryableLLMError) as e:
            logger.error(f"An error occured in stream response: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in stream response: {str(e)}", exc_info=True)
            raise

    def handle_message_start(self, event: RawMessageStartEvent) -> StreamingEvent:
        """Handle message start event."""
        logger.debug("===== Stream message started =====")
        return StreamingEvent(
            event_type=StreamingEventType.MESSAGE_START,
        )

    def handle_content_block_start(self, event: ContentBlockStartEvent) -> ToolUseBlock | None:
        """Handle content block start event."""
        if event.content_block.type == "tool_use":
            current_tool_use_block = ToolUseBlock(
                block_type=event.content_block.type,
                id=event.content_block.id,
                name=event.content_block.name,
                input={},
            )
            return current_tool_use_block
        return None

    def handle_content_block_delta(
        self, event: RawContentBlockDeltaEvent, tool_input_json: str
    ) -> tuple[StreamingEvent | None, str]:
        """Handle text token event."""
        if isinstance(event.delta, TextDelta):
            return StreamingEvent(
                event_type=StreamingEventType.TEXT_TOKEN,
                event_data=StreamingTextDelta(text=event.delta.text),
            ), tool_input_json
        elif isinstance(event.delta, InputJSONDelta):
            tool_input_json += event.delta.partial_json
            logger.debug(f"Updated tool input JSON: {tool_input_json}")
            return None, tool_input_json

    async def handle_content_block_stop(
        self, event: ContentBlockStopEvent, current_tool_use_block: ToolUseBlock, tool_input_json: str
    ) -> ToolResultBlock | None:
        """Handle content block stop event."""
        logger.debug("===== Stream content block ended =====")
        if event.content_block.type == "tool_use" and current_tool_use_block:
            try:
                # Parse accumulated JSON string into dict
                parsed_input = json.loads(tool_input_json)

                # Update the tool block with parsed input
                current_tool_use_block.tool_input = parsed_input

                # Get tool result
                tool_result = await self.handle_tool_call(tool_inputs=current_tool_use_block)
                return tool_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool input JSON: {tool_input_json}")
                logger.error(f"JSON parse error: {str(e)}")
                raise NonRetryableLLMError(
                    original_error=e, message="Failed to parse tool input JSON from LLM response"
                ) from e

    def handle_error(self, event: MessageStreamEvent) -> StreamingEvent:
        """Handle error event."""
        logger.error(f"===== Stream error: {event.error} =====")
        return StreamingEvent(
            event_type=StreamingEventType.ERROR,
            event_data=ErrorEvent(data={"error": event.error}),
        )

    def handle_message_stop(self, event: RawMessageStopEvent) -> StreamingEvent:
        """Handle message stop event."""
        logger.debug("===== Stream message ended =====")
        return StreamingEvent(
            event_type=StreamingEventType.MESSAGE_STOP,
        )

    async def handle_full_message(self, stream: AsyncStream[MessageStreamEvent]) -> StreamingEvent:
        """Handle full message event."""
        full_response = await stream.get_final_message()
        logger.debug(f"FULL ASSISTANT RESPONSE FOR DEBUGGING: {full_response}")

        content = []
        for block in full_response.content:
            if block.type == "text":
                content.append(TextBlock.model_validate(block.model_dump()))
            elif block.type == "tool_use":
                content.append(ToolUseBlock.model_validate(block.model_dump()))
            else:
                logger.warning(f"Unexpected block type in assistant message: {block.type}")

        return StreamingEvent(
            event_type=StreamingEventType.ASSISTANT_MESSAGE,
            event_data=AssistantMessageEvent(content=content),
        )

    async def handle_tool_call(self, tool_inputs: ToolUseBlock) -> ToolResultBlock:
        """Handle tool use event."""
        tool_result = await self.get_tool_result(tool_inputs)
        logger.debug(f"Tool result: {tool_result}")
        return tool_result

    async def get_tool_result(self, tool_inputs: ToolUseBlock) -> ToolResultBlock:
        """Handle tool use for specified tools."""
        try:
            if tool_inputs.tool_name == "rag_search":
                search_results = await self.use_rag_search(tool_inputs)
                if search_results is None:
                    # Special tool use block for no context
                    tool_result = ToolResultBlock(
                        tool_use_id=tool_inputs.tool_use_id,
                        content="No relevant context found for the original request.",
                    )
                else:
                    # Regular tool use block with context
                    tool_result = ToolResultBlock(
                        tool_use_id=tool_inputs.tool_use_id,
                        content=f"Here is context retrieved by RAG search: \n\n{search_results}\n\n."
                        f"Please use this context to answer my original request, if it's relevant.",
                    )

                return tool_result

            raise ValueError(f"Unknown tool: {tool_inputs.tool_name}")
        except Exception as e:
            logger.error(f"Error executing tool {tool_inputs.tool_name}: {str(e)}", exc_info=True)
            raise NonRetryableLLMError(
                original_error=e, message=f"An error occurred while handling tool: {str(e)}"
            ) from e

    # TODO: this method belongs to retriever
    async def use_rag_search(self, tool_inputs: ToolUseBlock) -> list[str] | None:
        """Perform RAG search using the provided tool input.

        Args:
            tool_inputs: ToolUseBlock containing the rag_query
        """
        # Get the query from tool input
        rag_query = tool_inputs.tool_input["rag_query"]  # This matches the new schema
        logger.debug(f"Using this query for RAG search: {rag_query}")
        # Merge these two methods
        multiple_queries = await self.generate_multi_query(rag_query)
        combined_queries = multiple_queries + [rag_query]

        # get ranked search results
        results = await self.retriever.retrieve(rag_query=rag_query, combined_queries=combined_queries, top_n=3)
        logger.debug(f"Retriever results: {results}")

        if not results:
            logger.warning("No search results found.")
            return None  # Return None if no results

        # Preprocess the results here
        preprocessed_results = await self.preprocess_ranked_documents(results)
        logger.debug(f"Processed results: {preprocessed_results}")

        return preprocessed_results

    @base_error_handler
    async def preprocess_ranked_documents(self, ranked_documents: list[dict[str, Any]]) -> list[str]:
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
    async def generate_multi_query(self, query: str, model: str | None = None, n_queries: int = 3) -> list[str]:
        """Generate multiple search queries from a single user query using Claude's tool use capability."""
        messages = [
            MessageParam(
                role="user",
                content=[
                    TextBlockParam(
                        type="text", text=f"Generate {n_queries} search queries for the following question: {query}"
                    ),
                ],
            )
        ]

        response = await self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=messages,
            tools=[self.tool_manager.get_tool(ToolName.MULTI_QUERY)],
            tool_choice=self.tool_manager.force_tool_choice(ToolName.MULTI_QUERY),
        )
        logger.debug(f"Multi query tool response: {response}")

        return self.parse_tool_response(response, n_queries)

    def parse_tool_response(self, response: Message, n_queries: int) -> list[str]:
        """Parse the tool response from the Anthropic API."""
        # Extract tool calls
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            logger.error("No tool use in response")
            raise ValueError("Claude failed to use the multi_query_tool")

        tool_input = tool_calls[0].input

        # Parse and validate the JSON response
        try:
            # Expect: {"queries": ["query1", "query2", ...]}
            if "queries" not in tool_input:
                raise KeyError("Response missing 'queries' key")

            queries = tool_input["queries"]
            if not isinstance(queries, list):
                raise ValueError(f"Expected list of queries, got {type(queries)}")

            if not all(isinstance(q, str) for q in queries):
                raise ValueError("All queries must be strings")

            if not queries:
                raise ValueError("Empty queries list returned")

            # Return exactly n_queries
            return queries[:n_queries]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse tool response: {tool_input}")
            raise ValueError(f"Invalid tool response format: {e}")
