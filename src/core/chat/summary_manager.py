# TODO: Review the need for this class. How is this managed in other RAG systems?
import json
import random
from uuid import UUID

import anthropic
from anthropic.types import Message, MessageParam, TextBlockParam

from src.core.chat.prompt_manager import PromptManager
from src.core.chat.tool_manager import ToolManager, ToolName
from src.infra.data.data_repository import DataRepository
from src.infra.decorators import anthropic_error_handler
from src.infra.external.supabase_manager import SupabaseManager
from src.infra.logger import get_logger
from src.infra.settings import get_settings
from src.models.content_models import Document, SourceSummary
from src.models.llm_models import PromptType
from src.services.data_service import DataService

logger = get_logger()
settings = get_settings()

MAX_RETRIES = 2


class SummaryManager:
    """Responsible for generating summaries for data sources loaded into the system."""

    def __init__(
        self,
        data_service: DataService | None = None,
        prompt_manager: PromptManager | None = None,
        tool_manager: ToolManager | None = None,
        n_samples_max: int = 5,
    ):
        """Initialize the SummaryManager."""
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.data_service = data_service
        self.prompt_manager = prompt_manager
        self.tool_manager = tool_manager
        self.n_samples_max = n_samples_max

    async def _prepare_data_for_summary(self, documents: list[Document]) -> tuple[list[str], list[str], list[Document]]:
        """Prepare the data for summary generation."""
        unique_urls = list(set(doc.metadata.source_url for doc in documents if doc.metadata.source_url))
        unique_titles = list(set(doc.metadata.title for doc in documents if doc.metadata.title))
        documents_sample = self._select_samples(documents)
        return unique_urls, unique_titles, documents_sample

    def _select_samples(self, documents: list[Document]) -> list[Document]:
        """Select representative document samples."""
        logger.debug(f"Selecting {self.n_samples_max} samples from {len(documents)} documents")
        if len(documents) <= self.n_samples_max:
            return documents
        return random.sample(documents, self.n_samples_max)

    def _format_summary_input(
        self, documents_sample: list[Document], unique_urls: list[str], unique_titles: list[str]
    ) -> str:
        """Format input data for summary generation."""
        return f"""
        Analyze this web content and provide a summary and keywords.

        Source URLs ({len(unique_urls)} total):
        {json.dumps(unique_urls, indent=2)}

        Document Titles ({len(unique_titles)} total):
        {json.dumps(unique_titles, indent=2)}

        Sample Content ({len(documents_sample)} documents):
        {json.dumps([{
            'title': doc.metadata.title,
            'url': doc.metadata.source_url,
            'content': doc.content[:500] + '...' if len(doc.content) > 500 else doc.content
        } for doc in documents_sample], indent=2)}

        Generate:
        1. A concise summary (100-150 words) describing the main topics and content type
        2. 5-10 specific keywords that appear in the content
        
        Return as JSON with 'summary' and 'keywords' fields.
        """

    @anthropic_error_handler
    async def generate_document_summary(
        self, source_id: UUID, documents_sample: list[Document], unique_urls: list[str], unique_titles: list[str]
    ) -> SourceSummary:
        """Generates a document summary and keywords based on documents and metadata."""
        input_text = self._format_summary_input(documents_sample, unique_urls, unique_titles)

        messages = [MessageParam(role="user", content=[TextBlockParam(type="text", text=input_text)])]
        logger.debug(f"Summary generation input: {messages}")
        response = await self.client.messages.create(
            model=settings.main_model,
            max_tokens=1024,
            messages=messages,
            system=self.prompt_manager.return_system_prompt(PromptType.SUMMARY_PROMPT),
            tools=[self.tool_manager.get_tool(ToolName.SUMMARY)],
            tool_choice=self.tool_manager.force_tool_choice(ToolName.SUMMARY),
        )
        logger.debug(f"Summary generation response: {response}")
        return self._parse_summary(response, source_id)

    def _parse_summary(self, response: Message, source_id: UUID) -> SourceSummary:
        """Parse the summary response from Claude."""
        try:
            # Get tool calls from response
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            if not tool_calls:
                raise ValueError("No tool use in response")

            # Parse the tool output
            tool_output = json.loads(tool_calls[0].input)
            logger.debug(f"Tool output: {tool_output}")

            return SourceSummary(
                source_id=source_id,
                summary=tool_output["summary"],
                keywords=tool_output["keywords"],
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse summary response: {e}")
            raise ValueError(f"Invalid summary format: {e}")


if __name__ == "__main__":
    import asyncio
    from uuid import UUID

    async def test_summary_generation() -> None:  # type: ignore
        # Initialize dependencies
        logger.info("Initializing dependencies...")
        supabase_manager = await SupabaseManager.create_async()
        data_repository = DataRepository(supabase_manager)
        data_service = DataService(data_repository)
        prompt_manager = PromptManager()
        tool_manager = ToolManager()

        # Create summary manager
        logger.info("Creating summary manager...")
        summary_manager = SummaryManager(
            data_service=data_service, prompt_manager=prompt_manager, tool_manager=tool_manager, n_samples_max=5
        )

        # Test source ID - you'll provide this
        source_id = UUID("123e4567-e89b-12d3-a456-426614174000")  # Replace with actual
        logger.info(f"Testing with source_id: {source_id}")

        try:
            # Fetch documents
            logger.info("Fetching documents...")
            documents = await data_service.get_documents_by_source(source_id=source_id)
            logger.info(f"Found {len(documents)} documents")

            # Prepare data
            logger.info("Preparing data for summary...")
            unique_urls, unique_titles, documents_sample = await summary_manager._prepare_data_for_summary(documents)
            logger.info(f"Selected {len(documents_sample)} sample documents")
            logger.info(f"Found {len(unique_urls)} unique URLs")
            logger.info(f"Found {len(unique_titles)} unique titles")

            # Generate summary
            logger.info("Generating summary...")
            summary = await summary_manager.generate_document_summary(
                source_id=source_id,
                documents_sample=documents_sample,
                unique_urls=unique_urls,
                unique_titles=unique_titles,
            )

            # Print results
            logger.info("Summary generation complete!")
            logger.info("=== Generated Summary ===")
            logger.info(f"Summary: {summary.summary}")
            logger.info("=== Keywords ===")
            logger.info(f"Keywords: {', '.join(summary.keywords)}")

        except Exception as e:
            logger.error(f"Error during testing: {e}", exc_info=True)
        finally:
            # Cleanup
            await supabase_manager.close()
            logger.info("Test complete")

    # Run the test
    asyncio.run(test_summary_generation())
