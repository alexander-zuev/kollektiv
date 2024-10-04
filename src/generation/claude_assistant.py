from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.vector_storage.vector_db import VectorDB  # Import only for type checking

import anthropic
import tiktoken
from anthropic.types import Message
from anthropic.types.beta.prompt_caching import PromptCachingBetaMessage

from src.generation.tool_definitions import tool_manager
from src.utils.config import ANTHROPIC_API_KEY
from src.utils.decorators import anthropic_error_handler, base_error_handler
from src.utils.logger import get_logger

logger = get_logger()


class ConversationMessage:

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
class ClaudeAssistant:
    """
    ClaudeAssistant is an AI assistant class with a focus on providing accurate, relevant, and helpful information
    utilizing a Retrieval Augmented Generation (RAG) system.

    :param api_key: API key used for authenticating with the Claude API service.
    :param model_name: Name of the language model to be used.
    """

    def __init__(
        self,
        vector_db: VectorDB,
        api_key: str = ANTHROPIC_API_KEY,
        model_name: str = "claude-3-5-sonnet-20240620",
    ):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.base_system_prompt = """
        You are an advanced AI assistant with access to various tools, including a powerful RAG (Retrieval Augmented
        Generation) system. Your primary function is to provide accurate, relevant, and helpful information to users
        by leveraging your broad knowledge base, analytical capabilities, and the specific information available
        through the RAG tool.
        Key guidelines:

        Use the RAG tool when queries likely require information from loaded documents or recent data not in your
        training.
        Carefully analyze the user's question and conversation context before deciding whether to use the RAG tool.
        When using RAG, formulate precise and targeted queries to retrieve the most relevant information.
        Seamlessly integrate retrieved information into your responses, citing sources when appropriate.
        If the RAG tool doesn't provide relevant information, rely on your general knowledge and analytical skills.
        Always strive for accuracy, clarity, and helpfulness in your responses.
        Be transparent about the source of your information (general knowledge vs. RAG-retrieved data).
        If you're unsure about information or if it's not in the loaded documents, clearly state your uncertainty.
        Provide context and explanations for complex topics, breaking them down into understandable parts.
        Offer follow-up questions or suggestions to guide the user towards more comprehensive understanding.

        Do not:

        Invent or hallucinate information not present in your knowledge base or the RAG-retrieved data.
        Use the RAG tool for general knowledge questions that don't require specific document retrieval.
        Disclose sensitive details about the RAG system's implementation or the document loading process.
        Provide personal opinions or biases; stick to factual information from your knowledge base and RAG system.
        Engage in or encourage any illegal, unethical, or harmful activities.
        Share personal information about users or any confidential data that may be in the loaded documents.

        Currently loaded document summaries:
        {document_summaries}
        Use these summaries to guide your use of the RAG tool and to provide context for the types of questions
        you can answer with the loaded documents.
        Interaction Style:

        Maintain a professional, friendly, and patient demeanor.
        Tailor your language and explanations to the user's apparent level of expertise.
        Ask for clarification when the user's query is ambiguous or lacks necessary details.

        Handling Complex Queries:

        For multi-part questions, address each part systematically.
        If a query requires multiple steps or a lengthy explanation, outline your approach before diving into details.
        Offer to break down complex topics into smaller, more manageable segments if needed.

        Continuous Improvement:

        Learn from user interactions to improve your query formulation for the RAG tool.
        Adapt your response style based on user feedback and follow-up questions.

        Remember to use your tools judiciously and always prioritize providing the most accurate,
        helpful, and contextually relevant information to the user. Adapt your communication style to
        the user's level of understanding and the complexity of the topic at hand.
        """
        self.system_prompt = self.base_system_prompt.format(document_summaries="No documents loaded yet.")
        self.conversation_history = None
        self.tool_manager = tool_manager
        self.tools: list[dict[str, Any]] = []
        self.extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"}
        self.retriever = None
        self.vector_db = vector_db

        self._init()

    @anthropic_error_handler
    def _init(self):
        self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=2)  # default number of re-tries
        self.conversation_history = ConversationHistory()

        self.tools = self.tool_manager.get_all_tools()  # Get all tools as a list of dicts
        logger.debug("Claude assistant successfully initialized.")

    @base_error_handler
    def _update_system_prompt(self, document_summaries: list[dict[str, Any]]):
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
        logger.debug(f"Processed results: {results}")

        return preprocessed_results

    @anthropic_error_handler
    def generate_document_summary(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        # Aggregate metadata
        unique_urls = {chunk["metadata"]["source_url"] for chunk in chunks}
        unique_titles = {chunk["metadata"]["page_title"] for chunk in chunks}

        # Select diverse content samples
        sample_chunks = self._select_diverse_chunks(chunks, 15)
        content_samples = [chunk["data"]["text"][:300] for chunk in sample_chunks]

        # Construct the summary prompt
        system_prompt = """
        You are a Document Analysis AI. Your task is to generate accurate, relevant and concise document summaries and
        a list of key topics (keywords) based on a subset of chunks shown to you. Always respond in the following JSON
        format.

        General instructions:
        1. Provide a 150-200 word summary that captures the essence of the documentation.
        2. Mention any notable features or key points that stand out.
        3. If applicable, briefly describe the type of documentation (e.g., API reference, user guide, etc.).
        4. Do not use phrases like "This documentation covers" or "This summary describes". Start directly
        with the key information.

        JSON Format:
        {
          "summary": "A concise summary of the document",
          "keywords": ["keyword1", "keyword2", "keyword3", ...]
        }

        Ensure your entire response is a valid JSON
        """

        user_message = f"""
        Analyze the following document and provide a list of keywords (key topics).

        Document Metadata:
        - Unique URLs: {len(unique_urls)}
        - Unique Titles: {unique_titles}

        Content Structure:
        {self._summarize_content_structure(chunks)}

        Chunk Samples:
        {self._format_content_samples(content_samples)}

        """

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=450,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        summary, keywords = self._parse_summary(response)

        return {
            "summary": summary,
            "keywords": keywords,
        }

    @base_error_handler
    def _parse_summary(self, response: Message):
        """Takes an Anthropic Message object
        Returns a dictionary with keys:
        - summary: generated document summary
        - keywords: generated list of keywords"""

        content = response.content[0].text
        logger.debug(f"Attempting to parse the summary json: {content}")
        try:
            parsed = json.loads(content)
            return parsed["summary"], parsed["keywords"]
        except json.JSONDecodeError:
            logger.error("Error: Response is not valid JSON")
            return self._extract_data_from_text(content)
        except KeyError as e:
            logger.error(f"Error: JSON does not contain expected keys: {e}")
            return self._extract_data_from_text(content)

    @base_error_handler
    def _extract_data_from_text(self, text):
        # Fallback method to extract data if JSON parsing fails
        summary = ""
        keywords = []
        if "summary:" in text.lower():
            summary = text.lower().split("summary:")[1].split("keywords:")[0].strip()
        if "keywords:" in text.lower():
            keywords = text.lower().split("keywords:")[1].strip().split(",")
        return summary, [k.strip() for k in keywords]

    def _select_diverse_chunks(self, chunks: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
        step = max(1, len(chunks) // n)
        return chunks[::step][:n]

    def _summarize_content_structure(self, chunks: list[dict[str, Any]]) -> str:
        # Analyze the structure based on headers
        header_structure = {}
        for chunk in chunks:
            headers = chunk["data"]["headers"]
            for level, header in headers.items():
                if header:
                    header_structure.setdefault(level, set()).add(header)

        return "\n".join([f"{level}: {', '.join(headers)}" for level, headers in header_structure.items()])

    def _format_content_samples(self, samples: list[str]) -> str:
        return "\n\n".join(f"Sample {i + 1}:\n{sample}" for i, sample in enumerate(samples))

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
            model="claude-3-5-sonnet-20240620",
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
