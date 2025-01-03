# TODO: Review the need for this class. How is this managed in other RAG systems?
from typing import Any

import anthropic

from src.infra.decorators import anthropic_error_handler
from src.infra.logger import get_logger
from src.infra.settings import settings
from src.services.data_service import DataService

logger = get_logger()

MAX_RETRIES = 2


class SummaryManager:
    """Responsible for generating summaries for data sources loaded into the system."""

    def __init__(self, data_service: DataService | None = None):
        """Initialize the SummaryManager."""
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.data_service = data_service

    #
    async def _prepare_data_for_summary(self, source_id: str) -> None:
        """Prepare the data for summary generation."""
        # Fetches a list of unique links
        # Fetches random documents
        pass

    # Add summary prompt to the manager

    @anthropic_error_handler
    async def generate_document_summary(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Generates a document summary and keywords based on provided chunks.

        Args:
            chunks: A list of dictionaries, where each dictionary represents a chunk of text and its metadata.

        Returns:
            A dictionary containing the generated summary and keywords.
        """
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

        message = f"""
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
            messages=[{"role": "user", "content": message}],
        )

        summary, keywords = self._parse_summary(response)

        return {
            "summary": summary,
            "keywords": keywords,
        }
