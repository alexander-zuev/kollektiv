from src.utils.logger import setup_logger
from src.utils.config import ANTHROPIC_API_KEY
from src.utils.decorators import error_handler
from typing import Dict, Any, List

import anthropic
import os

logger = setup_logger('claude_assistant', "claude_assistant.log")

# Client Class
class ClaudeAssistant:
    def __init__(self, api_key :str =ANTHROPIC_API_KEY, model_name:str ="claude-3-5-sonnet-20240620"):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logger
        self.system_prompt = ""
        self.conversation_history = []

    @error_handler(logger)
    def init(self):
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.logger.info("Successfully initialized Anthropic client")


    @error_handler(logger)
    def get_response(self, user_query: str, streaming: bool = False):
        pass

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
    def generate_multi_query(self, query: str, model: str = None, n_queries: int = 5) -> List[str]:
        prompt = f"""
        You are an AI assistant whose task is to generate multiple queries as part of a RAG system.
        You are helping users retrieve relevant information from a vector database.
        For the given user question, formulate up to {n_queries} related, relevant questions to assist in finding the 
        information.

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
            system = prompt,
            messages=[
                {"role": "user", "content": query}
            ]
        )

        content = message.content[0].text
        content = content.split('\n')
        return content

    @error_handler(logger)
    def combine_queries(self, user_query: str, generated_queries: List[str]) -> List[str]:
        """
        Combines user query and generated queries into a list, removing any empty queries.
        """
        combined_queries = [query for query in [user_query] + generated_queries if query.strip()]
        return combined_queries

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