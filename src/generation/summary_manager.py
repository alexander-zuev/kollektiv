import json
import os
from typing import Any

import anthropic
import weave
from anthropic.types import Message

from utils.config import ANTHROPIC_API_KEY, MAIN_MODEL, VECTOR_STORAGE_DIR, WEAVE_PROJECT_NAME
from utils.decorators import anthropic_error_handler, base_error_handler
from utils.logger import get_logger

logger = get_logger()

MAX_RETRIES = 2


class SummaryManager:
    """Support class that manages document summaries that are loaded into the vector database"""

    def __init__(self, client: anthropic.Anthropic, model_name: str = MAIN_MODEL):
        weave.init(project_name=WEAVE_PROJECT_NAME)
        self.summaries = self.load_summaries()
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=MAX_RETRIES)
        self.model_name = model_name

    @anthropic_error_handler
    def generate_document_summary(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
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

    @base_error_handler
    def _select_diverse_chunks(self, chunks: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
        """Selects a diverse subset of chunks.

        Args:
            chunks: The list of chunks to select from.
            n: The desired number of chunks to select.

        Returns:
            A list of selected chunks.
        """
        step = max(1, len(chunks) // n)
        return chunks[::step][:n]

    @base_error_handler
    def _summarize_content_structure(self, chunks: list[dict[str, Any]]) -> str:
        """Summarizes the content structure based on headers.

        Args:
            chunks: The list of chunks.

        Returns:
            A string summarizing the content structure.
        """
        header_structure = {}
        for chunk in chunks:
            headers = chunk["data"]["headers"]
            for level, header in headers.items():
                if header:
                    header_structure.setdefault(level, set()).add(header)

        return "\n".join([f"{level}: {', '.join(headers)}" for level, headers in header_structure.items()])

    @base_error_handler
    def _format_content_samples(self, samples: list[str]) -> str:
        """Formats content samples for display.

        Args:
            samples: A list of content samples.

        Returns:
            A formatted string of content samples.
        """
        return "\n\n".join(f"Sample {i + 1}:\n{sample}" for i, sample in enumerate(samples))

    @base_error_handler
    def _parse_summary(self, response: Message):
        """Parses the summary and keywords from an Anthropic Message.

        Args:
            response: The Anthropic Message object.

        Returns:
            A tuple containing the summary and a list of keywords.
        """
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
        """Extracts summary and keywords from text if JSON parsing fails.

        This method acts as a fallback mechanism when the model's response
        doesn't adhere to the expected JSON format. It attempts to extract
        the summary and keywords by splitting the text based on predefined
        delimiters.

        Args:
            text: The raw text from the model's response.

        Returns:
            A tuple containing the extracted summary and a list of keywords.
        """
        summary = ""
        keywords = []
        if "summary:" in text.lower():
            summary = text.lower().split("summary:")[1].split("keywords:")[0].strip()
        if "keywords:" in text.lower():
            keywords = text.lower().split("keywords:")[1].strip().split(",")
        return summary, [k.strip() for k in keywords]

    @base_error_handler
    def load_summaries(self) -> dict[str, dict[str, Any]]:
        """Loads document summaries from a JSON file.

        Returns:
            A dictionary where keys are document IDs and values are dictionaries
            containing the summary and keywords for each document.
            Returns an empty dictionary if the summaries file does not exist or
            if there is an error loading the file.
        """
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        if os.path.exists(summaries_file):
            try:
                with open(summaries_file) as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to load document summaries: {e}")
                return {}
        else:
            return {}

    @base_error_handler
    def save_summaries(self):
        """Saves the document summaries to a JSON file."""
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        try:
            with open(summaries_file, "w") as f:
                json.dump(self.document_summaries, f, indent=2)
                logger.info(f"Successfully saved new document summary to {summaries_file}")
        except Exception as e:
            logger.error(f"Failed to save document summaries: {e}")

    @base_error_handler
    def get_all_summaries(self) -> list[str]:
        """Returns a list of all document summaries."""
        return list(self.document_summaries.values())

    @base_error_handler
    def clear_summaries(self):
        """Clears the document summaries and removes the summaries file."""
        self.summaries = {}
        summaries_file = os.path.join(VECTOR_STORAGE_DIR, "document_summaries.json")
        if os.path.exists(summaries_file):
            os.remove(summaries_file)
            logger.info("Document summaries cleared.")
        self.save_summaries()

    @base_error_handler
    def process_file(self, data: list[dict], file_name: str):
        if file_name in self.summaries:
            result = self.summaries[file_name]
            logger.info(f"Loading existing summary for {file_name}.")
        else:
            logger.info(f"Summary for {file_name} not found, generating new one.")
            result = self.generate_document_summary(data)
            result["filename"] = file_name
            self.summaries[file_name] = result

        # Save updated summaries
        self.save_summaries()
