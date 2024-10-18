from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import anthropic
import tiktoken
import weave
from anthropic.types import Message
from anthropic.types.beta.prompt_caching import PromptCachingBetaMessage
from pydantic import ConfigDict, Field
from weave import Model

from src.generation.tool_definitions import tool_manager
from src.utils.config import ANTHROPIC_API_KEY, MAIN_MODEL, WEAVE_PROJECT_NAME
from src.utils.decorators import anthropic_error_handler, base_error_handler
from src.utils.logger import get_logger
from src.vector_storage.vector_db import VectorDB

weave.init(WEAVE_PROJECT_NAME)


logger = get_logger()


class ConversationMessage:
    """
    Represent a conversation message with an ID, role, and content.

    Args:
        role (str): The role of the message sender (e.g., 'user', 'system').
        content (str | list[dict[str, Any]]): The content of the message, which can be a string or a list of dictionaries.

    Returns:
        None

    Raises:
        None
    """

    def __init__(self, role: str, content: str | list[dict[str, Any]]):
        self.id = str(uuid.uuid4())
        self.role = role
        self.content = content

    def to_dict(self, include_id: bool = False) -> dict[str, Any]:
        message_dict = {"role": self.role, "content": self.content}
        if include_id:
            message_dict["id"] = self.id
        return message_dict


class ConversationHistory:
    """
    Manage the history of a conversation, including token counts and message handling.

    Args:
        max_tokens (int): Maximum number of tokens allowed in the conversation history (default is 200000).
        tokenizer (str): The tokenizer encoding to use (default is "cl100k_base").

    class ConversationHistory:
        def __init__(self, max_tokens: int = 200000, tokenizer: str = "cl100k_base"):
    """

    def __init__(self, max_tokens: int = 200000, tokenizer: str = "cl100k_base"):
        self.max_tokens = max_tokens  # specifically for Sonnet 3.5
        self.messages: list[ConversationMessage] = []
        self.total_tokens = 0
        self.tokenizer = tiktoken.get_encoding(tokenizer)

    def add_message(self, role: str, content: str | list[dict[str, Any]]) -> None:
        message = ConversationMessage(role, content)
        self.messages.append(message)
        logger.debug(f"Added message for role={message.role}")

        # estimate tokens for user messages
        if role == "user":
            estimated_tokens = self._estimate_tokens(content)
            if self.total_tokens + estimated_tokens > self.max_tokens:
                self._prune_history(estimated_tokens)
            self.total_tokens += estimated_tokens

    def update_token_count(self, input_tokens: int, output_tokens: int) -> None:
        self.total_tokens = input_tokens + output_tokens
        if self.total_tokens > self.max_tokens:
            self._prune_history(0)

    def _estimate_tokens(self, content: str | list[dict[str, Any]]) -> int:
        if isinstance(content, str):
            return len(self.tokenizer.encode(content))
        elif isinstance(content, list):
            return sum(
                len(self.tokenizer.encode(item["text"]))
                for item in content
                if isinstance(item, dict) and "text" in item
            )
        return 0

    def _prune_history(self, new_tokens: int) -> None:
        while self.total_tokens + new_tokens > self.max_tokens * 0.9 and len(self.messages) > 1:
            removed_message = self.messages.pop(0)
            # We don't know the exact token count of the removed message, so we estimate
            self.total_tokens -= self._estimate_tokens(removed_message.content)

    def remove_last_message(self) -> None:
        if self.messages:
            removed_message = self.messages.pop()
            logger.info(f"Removed message: {removed_message.role}")

    def get_conversation_history(self, debug: bool = False) -> list[dict[str, Any]]:
        return [msg.to_dict(include_id=debug) for msg in self.messages]

    def log_conversation_state(self) -> None:
        logger.debug(f"Conversation state: messages={len(self.messages)}, " f"Total tokens={self.total_tokens}, ")


# Client Class
class ClaudeAssistant(Model):
    """
    Define the ClaudeAssistant class for interacting with the Anthropoc API and managing conversational history.

    Args:
        vector_db (VectorDB): An instance of VectorDB for handling vector database operations.
        api_key (str, optional): API key for authenticating with the Anthropoc service. Defaults to None.
        model_name (str, optional): Name of the model to use for generating responses. Defaults to None.

    Attributes:
        client (anthropic.Anthropic | None): Instance for handling API interactions.
        vector_db (VectorDB): Instance for handling vector database operations.
        api_key (str): API key for the Anthropoc service.
        model_name (str): Name of the model to use for generating responses.
        base_system_prompt (str): Base prompt template for the system.
        system_prompt (str): Current system prompt.
        conversation_history (ConversationHistory | None): History of the conversation.
        retrieved_contexts (list[str]): List of retrieved contexts.
        tool_manager (Any): Manager for handling tools.
        tools (list[dict[str, Any]]): List of available tools.
        extra_headers (dict[str, str]): Extra headers for API requests.
        retriever (Any | None): Instance for handling data retrieval.

    Methods:
        __init__(self, vector_db, api_key=None, model_name=None): Initialize the assistant with the given parameters.
        _init(self): Initialize the Anthropoc client and conversation history.
        update_system_prompt(self, document_summaries): Update the system prompt with document summaries.
        cached_system_prompt(self): Get the cached system prompt.
        cached_tools(self): Get the cached tools.
        preprocess_user_input(self, input_text): Preprocess user input text.
        get_response(self, user_input, stream=True): Generate a response based on user input.
        stream_response(self, user_input): Stream responses as they are generated.
    """

    client: anthropic.Anthropic | None = None
    vector_db: VectorDB
    api_key: str = Field(default=ANTHROPIC_API_KEY)
    model_name: str = Field(default=MAIN_MODEL)
    base_system_prompt: str = Field(default="")
    system_prompt: str = Field(default="")
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
        api_key: str = None,
        model_name: str = None,
    ):
        # Initialize fields via super().__init__()
        super().__init__(
            client=None,
            vector_db=vector_db,
            api_key=api_key or ANTHROPIC_API_KEY,
            model_name=model_name or MAIN_MODEL,
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
    def _init(self):
        self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=2)  # default number of re-tries
        self.conversation_history = ConversationHistory()

        self.tools = self.tool_manager.get_all_tools()  # Get all tools as a list of dicts
        logger.debug("Claude assistant successfully initialized.")

    @base_error_handler
    def update_system_prompt(self, document_summaries: list[dict[str, Any]]):
        """
        :param document_summaries: List of dictionaries containing summary information to be incorporated into
        the system prompt.
        :return: None
        """
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
    def cached_system_prompt(self) -> list[dict[str, Any]]:
        return [{"type": "text", "text": self.system_prompt, "cache_control": {"type": "ephemeral"}}]

    @base_error_handler
    def cached_tools(self) -> list[dict[str, Any]]:
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
    def preprocess_user_input(self, input_text: str) -> str:
        # Remove any leading/trailing whitespace
        cleaned_input = input_text.strip()
        # Replace newlines with spaces
        cleaned_input = " ".join(cleaned_input.split())
        return cleaned_input

    @anthropic_error_handler
    def get_response(self, user_input: str, stream: bool = True) -> Generator[str] | str:
        """
        :param stream: controls whether output is streamed or not
        :param user_input: The input string provided by the user to generate a response.
        :return: A string response generated by the assistant based on the user input, potentially augmented with
         results from tool usage.
        """

        if stream:
            assistant_response_stream = self.stream_response(user_input)
            return assistant_response_stream

        else:
            assistant_response = self.not_stream_response(user_input)
            return assistant_response

    @anthropic_error_handler
    @weave.op()
    def stream_response(self, user_input: str) -> Generator[str]:
        # iteration = 0
        user_input = self.preprocess_user_input(user_input)
        self.conversation_history.add_message(role="user", content=user_input)
        logger.debug(
            f"Printing conversation history for debugging: {self.conversation_history.get_conversation_history()}"
        )

        while True:

            try:
                messages = self.conversation_history.get_conversation_history()
                with self.client.messages.stream(
                    messages=messages,
                    system=self.cached_system_prompt(),
                    max_tokens=8192,
                    model=self.model_name,
                    tools=self.cached_tools(),
                    extra_headers=self.extra_headers,
                ) as stream:
                    for event in stream:
                        # logger.debug(event) enable for debugging
                        if event.type == "text":
                            # yield event.text
                            yield {"type": "text", "content": event.text}

                        elif event.type == "content_block_stop":
                            if event.content_block.type == "tool_use":
                                logger.debug(f"Tool use detected: {event.content_block.name}")
                                yield {"type": "tool_use", "tool": event.content_block.name}
                        elif event.type == "message_stop":
                            logger.debug("===== Stream message ended =====")

                # Get the final message after consuming the entire stream
                assistant_response = stream.get_final_message()
                self._process_assistant_response(assistant_response)

                # Handle tool use if present in the final message
                tool_use_block = next((block for block in assistant_response.content if block.type == "tool_use"), None)
                if tool_use_block:
                    tool_result = self.handle_tool_use(tool_use_block.name, tool_use_block.input, tool_use_block.id)
                    logger.debug(f"Tool result: {tool_result}")

                # Only break if no tool was used
                if not tool_use_block:
                    break

            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                self.conversation_history.remove_last_message()
                raise Exception(f"An error occurred: {str(e)}") from e

    @anthropic_error_handler
    @weave.op()
    def not_stream_response(self, user_input: str) -> str:
        user_input = self.preprocess_user_input(user_input)
        self.conversation_history.add_message(role="user", content=user_input)
        logger.debug(
            f"Printing conversation history for debugging: {self.conversation_history.get_conversation_history()}"
        )

        try:
            while True:
                messages = self.conversation_history.get_conversation_history()
                response = self.client.beta.prompt_caching.messages.create(
                    messages=messages,
                    system=self.cached_system_prompt(),
                    max_tokens=8192,
                    model=self.model_name,
                    tools=self.cached_tools(),
                )

                # tool use
                if response.stop_reason == "tool_use":
                    assistant_response = self._process_assistant_response(response)  # save the first response
                    print(f"Assistant: Using a 🔨tool: {assistant_response}")

                    tool_use = next(block for block in response.content if block.type == "tool_use")

                    tool_result = self.handle_tool_use(tool_use.name, tool_use.input, tool_use.id)
                    logger.debug(f"Tool result: {tool_result}")

                # not a tool use
                else:
                    assistant_response = self._process_assistant_response(response)
                    return assistant_response

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            self.conversation_history.remove_last_message()
            raise Exception(f"An error occurred: {str(e)}") from e

    @base_error_handler
    def _process_assistant_response(self, response: PromptCachingBetaMessage | Message) -> str:
        """
        Process the assistant's response by saving the message and updating the token count.
        """

        logger.debug(
            f"Cached {response.usage.cache_creation_input_tokens} input tokens. \n"
            f"Read {response.usage.cache_read_input_tokens} tokens from cache"
        )
        self.conversation_history.add_message(role="assistant", content=response.content)
        self.conversation_history.update_token_count(response.usage.input_tokens, response.usage.output_tokens)
        logger.debug(
            f"Processed assistant response. Updated conversation history: "
            f"{self.conversation_history.get_conversation_history()}"
        )

        return response.content[0].text

    @base_error_handler
    def handle_tool_use(self, tool_name: str, tool_input: dict[str, Any], tool_use_id: str) -> dict[str, Any] | str:

        try:
            if tool_name == "rag_search":
                search_results = self.use_rag_search(tool_input=tool_input)

                tool_result = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Here is context retrieved by RAG search: \n\n{search_results}\n\n."
                            f"Now please try to answer my original request.",
                        }
                    ],
                }

                # save message to conversation history
                self.conversation_history.add_message(**tool_result)
                logger.debug(
                    f"Debugging conversation history after tool use: "
                    f"{self.conversation_history.get_conversation_history()}"
                )
                return tool_result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return f"Error: {str(e)}"

    @anthropic_error_handler
    @weave.op()
    def formulate_rag_query(self, recent_conversation_history: list[dict[str, Any]], important_context: str) -> str:
        """ "
        Generates a rag search query based on recent conversation history and important context generated by AI
        assistant."""
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
        """Retrieves last 6 messages (3 user messages + 3 assistant messages)"""
        recent_messages = self.conversation_history.messages[-n_messages:]
        return [msg.to_dict() for msg in recent_messages]

    @base_error_handler
    def use_rag_search(self, tool_input: dict[str, Any]) -> list[str]:
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
        Converts ranked documents into a structured string for passing to the Claude API.
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
    def generate_multi_query(self, query: str, model: str = None, n_queries: int = 5) -> list[str]:
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
        Combines user query and generated queries into a list, removing any empty queries.
        """
        combined_queries = [query for query in [user_query] + generated_queries if query.strip()]
        return combined_queries

    @anthropic_error_handler
    @weave.op()
    async def predict(self, question: str) -> dict:
        """Should match the keys in the Dataset that is passed for evaluation"""
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

    def reset_conversation(self):
        self.conversation_history = ConversationHistory()
        self.retrieved_contexts = []
