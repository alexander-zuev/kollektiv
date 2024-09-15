import anthropic

from src.utils.config import ANTHROPIC_API_KEY
from src.utils.decorators import error_handler
from src.utils.logger import setup_logger

logger = setup_logger(__name__, "query_generator.log")


class QueryGenerator:
    def __init__(self, api_key: str = ANTHROPIC_API_KEY, model_name: str = "claude-3-5-sonnet-20240620"):
        self.client = anthropic.Client(api_key=api_key)
        self.model_name = model_name
        self.logger = setup_logger(__name__, "logging.log")

    @error_handler(logger)
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

    @error_handler(logger)
    def combine_queries(self, user_query: str, generated_queries: list[str]) -> list[str]:
        """
        Combines user query and generated queries into a list, removing any empty queries.
        """
        combined_queries = [query for query in [user_query] + generated_queries if query.strip()]
        return combined_queries
