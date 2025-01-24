from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterable
from typing import Any, cast
from uuid import UUID

import anthropic
import weave
from anthropic.types import (
    InputJSONDelta,
    Message,
    MessageParam,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextBlockParam,
    TextDelta,
    ToolParam,
)
from anthropic.types.message_stream_event import MessageStreamEvent
from pydantic import ConfigDict, Field
from weave import Model

from src.core._exceptions import NonRetryableLLMError
from src.core.chat.prompt_manager import PromptManager
from src.core.chat.tool_manager import ToolManager
from src.core.search.retriever import Retriever
from src.infra.decorators import (
    anthropic_error_handler,
    base_error_handler,
)
from src.infra.logger import _truncate_message, get_logger
from src.infra.settings import get_settings
from src.models.chat_models import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    ConversationHistory,
    MessageDeltaEvent,
    MessageStartEvent,
    MessageStopEvent,
    StreamErrorEvent,
    StreamEvent,
    StreamEventType,
    TextBlock,
    TextDeltaStream,
    ToolInputJSONStream,
    ToolResultBlock,
    ToolUseBlock,
)
from src.models.llm_models import SystemPrompt, Tool, ToolName

settings = get_settings()
logger = get_logger()


class ClaudeAssistant(Model):
    """
    Define the ClaudeAssistant class for managing AI assistant functionalities with various tools and configurations.

    Args:
        retriever (Retriever): The retriever instance for RAG operations.
        api_key (str, optional): The API key for the Anthropic client. Defaults to ANTHROPIC_API_KEY.
        model_name (str, optional): The name of the model to use. Defaults to MAIN_MODEL.

    Raises:
        anthropic.exceptions.AnthropicError: If there's an error initializing the Anthropic client.
        NonRetryableLLMError: If there's an error initializing dependencies.
    """

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
            api_key=api_key or settings.anthropic_api_key,
            model_name=model_name or settings.main_model,
        )

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key, max_retries=2)
        self.tools = [Tool.from_tool_param(self.tool_manager.get_tool(ToolName.RAG_SEARCH))]
        self.system_prompt = self.prompt_manager.get_system_prompt(document_summary_prompt="NO DOCUMENTS LOADED YET")
        self.retriever = retriever
        logger.info("✓ Initialized Claude assistant successfully")

    # TODO: this method needs to be refactored completely and use Supabase stored summaries
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
    async def stream_response(self, conv_history: ConversationHistory) -> AsyncGenerator[StreamEvent, None]:
        """Setups a stream response for a conversation.

        Key architechtural decisions:
        - stream_response is a "dumb" streamer. It's purpose is just to convert Anthropic stream events upwards.
        1. Calls Anthropic API
        2. Converts events to our format
        3. Yields them immediately
        """
        logger.debug(f"Number of messages in conversation history: {len(conv_history.messages)}")

        # 1. Build conversation historry in Anthropic API format
        messages = conv_history.to_anthropic_messages()
        logger.debug(_truncate_message(f"Debugging messages list for Anthropic API: {messages}"))

        # 2. Setup stream
        async with self.client.messages.stream(
            messages=messages,
            system=self.cached_system_prompt,
            max_tokens=8192,
            model=self.model_name,
            tools=self.cached_tools,
            extra_headers=self.extra_headers,
        ) as stream:
            async for event in stream:
                match event.type:
                    case RawMessageStartEvent():
                        yield self.handle_message_start(cast(RawMessageStartEvent, event))
                    case "content_block_start":
                        yield self.handle_content_block_start(cast(RawContentBlockStartEvent, event))
                    case "content_block_delta":
                        yield self.handle_content_block_delta(cast(RawContentBlockDeltaEvent, event))
                    case "content_block_stop":
                        yield self.handle_content_block_stop(cast(RawContentBlockStopEvent, event))
                    case "message_delta":
                        yield self.handle_message_delta(cast(RawMessageDeltaEvent, event))
                    case "message_stop":
                        yield self.handle_message_stop(cast(RawMessageStopEvent, event))
                    case "error":
                        yield self.handle_error(cast(MessageStreamEvent, event))

    def handle_message_start(self, event: RawMessageStartEvent) -> StreamEvent:
        """Handle message start event."""
        logger.debug("===== Stream message started =====")
        return StreamEvent(
            event_type=StreamEventType.MESSAGE_START,
            data=MessageStartEvent(),
        )

    def handle_content_block_start(self, event: RawContentBlockStartEvent) -> StreamEvent:
        """Handle content block start event."""
        logger.debug("===== Stream content block started =====")
        match event.content_block.type:
            case "text":
                text_block = TextBlock(index=event.index, text=event.content_block.text)
                return StreamEvent(
                    event_type=StreamEventType.CONTENT_BLOCK_START,
                    data=ContentBlockStartEvent(
                        index=event.index,
                        content_block=text_block,
                    ),
                )
            case "tool_use":
                tool_use_block = ToolUseBlock(
                    index=event.index,
                    id=event.content_block.id,
                    name=event.content_block.name,
                    input=event.content_block.input,
                )
                return StreamEvent(
                    event_type=StreamEventType.CONTENT_BLOCK_START,
                    data=ContentBlockStartEvent(
                        index=event.index,
                        content_block=tool_use_block,
                    ),
                )

    def handle_content_block_delta(self, event: RawContentBlockDeltaEvent) -> StreamEvent:
        """Handles content block delta events."""
        match event.delta:
            case TextDelta():
                text_delta = ContentBlockDeltaEvent(
                    type=StreamEventType.CONTENT_BLOCK_DELTA,
                    delta=TextDeltaStream(text=event.delta.text),
                )
                return StreamEvent(
                    event_type=StreamEventType.CONTENT_BLOCK_DELTA,
                    data=text_delta,
                )
            case InputJSONDelta():
                tool_input_json_delta = ContentBlockDeltaEvent(
                    type=StreamEventType.CONTENT_BLOCK_DELTA,
                    delta=ToolInputJSONStream(partial_json=event.delta.partial_json),
                )
                return StreamEvent(
                    event_type=StreamEventType.CONTENT_BLOCK_DELTA,
                    data=tool_input_json_delta,
                )
            case _:
                logger.error(f"Unexpected content block delta type: {event.delta}")
                raise ValueError(f"Unexpected content block delta type: {event.delta}")

    def handle_content_block_stop(
        self,
        event: RawContentBlockStopEvent,
    ) -> StreamEvent:
        """Handle content block stop event."""
        logger.debug("===== Content block stop event =====")
        return StreamEvent(
            event_type=StreamEventType.CONTENT_BLOCK_STOP,
            data=ContentBlockStopEvent(
                index=event.index,
            ),
        )

    def handle_message_delta(self, event: RawMessageDeltaEvent) -> StreamEvent:
        """Handle message delta event."""
        logger.debug("===== Message delta event =====")
        return StreamEvent(
            event_type=StreamEventType.MESSAGE_DELTA,
            data=MessageDeltaEvent(delta=event.delta.model_dump(), usage=event.usage.model_dump()),
        )

    def handle_message_stop(self, event: RawMessageStopEvent) -> StreamEvent:
        """Handle message stop event."""
        logger.debug("===== Stream message ended =====")
        return StreamEvent(
            event_type=StreamEventType.MESSAGE_STOP,
            data=MessageStopEvent(),
        )

    def handle_error(self, event: MessageStreamEvent) -> StreamEvent:
        """Handle error event."""
        logger.error(f"===== Stream error: {event.error} =====")
        return StreamEvent(
            event_type=StreamEventType.ERROR,
            data=StreamErrorEvent(error=event.error),
        )

    async def get_tool_result(self, tool_use_block: ToolUseBlock, user_id: UUID) -> ToolResultBlock:
        """Handle tool use for specified tools."""
        try:
            if tool_use_block.name == ToolName.RAG_SEARCH:
                search_results = await self.use_rag_search(tool_use_block, user_id)
                if search_results is None:
                    # Special tool use block for no context
                    tool_result = ToolResultBlock(
                        tool_use_id=tool_use_block.id,
                        content="No relevant context found for the original request.",
                    )
                    return tool_result
                else:
                    # Regular tool use block with context
                    tool_result = ToolResultBlock(
                        tool_use_id=tool_use_block.id,
                        content=f"Here is context retrieved by RAG search: \n\n{search_results}\n\n."
                        f"Please use this context to answer my original request, if it's relevant.",
                    )
                    return tool_result
            raise ValueError(f"Unknown tool: {tool_use_block.name}")
        except Exception as e:
            logger.error(f"Error executing tool {tool_use_block.name}: {str(e)}", exc_info=True)
            raise NonRetryableLLMError(
                original_error=e, message=f"An error occurred while handling tool: {str(e)}"
            ) from e

    # TODO: this method belongs to retriever, it should not have user_id as an argument (naughty, naughty)
    async def use_rag_search(self, tool_inputs: ToolUseBlock, user_id: UUID) -> list[str] | None:
        """Perform RAG search using the provided tool input.

        Args:
            tool_inputs: ToolUseBlock containing the rag_query
        """
        # Get the query from tool input
        if not isinstance(tool_inputs.input, dict):
            logger.error(f"Tool input is not a dictionary: {tool_inputs.input}")
            return None
        rag_query = tool_inputs.input.get("rag_query")  # This matches the new schema
        if not rag_query:
            logger.error(f"rag_query not found in tool input: {tool_inputs.input}")
            return None
        logger.debug(f"Using this query for RAG search: {rag_query}")
        # Merge these two methods
        multiple_queries = await self.generate_multi_query(rag_query)
        combined_queries = multiple_queries + [rag_query]

        # get ranked search results
        results = await self.retriever.retrieve(
            rag_query=rag_query, combined_queries=combined_queries, top_n=3, user_id=user_id
        )

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
            formatted_document = f"Document's relevance score: {relevance_score}: \nDocument text: {text}: \n--------\n"
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
