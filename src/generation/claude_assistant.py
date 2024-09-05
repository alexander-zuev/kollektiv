from csv import excel_tab

from src.utils.logger import setup_logger
from src.utils.config import ANTHROPIC_API_KEY, LOG_DIR
from typing import Dict, Any, List

import anthropic
import os

# Client Class
class Claude:
    def __init__(self, api_key :str =ANTHROPIC_API_KEY, model_name:str ="claude-3-5-sonnet-20240620"):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.logger = setup_logger('claude_assistant', os.path.join(LOG_DIR,
                                                                    "claude_assistant.log"))

    def init(self, ):
        try:
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
            )
            self.logger.info("Successfully initialized Anthropic client")
        except Exception as e:
            self.logger.error(f"Exception while initializing Anthropic client: {e}")
            raise


    def get_response(self, user_query: str, streaming: bool = False):
        pass

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

            # self.logger.debug(f"Printing pre-processed preprocessed_context {formatted_document}")

        return preprocessed_context

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
