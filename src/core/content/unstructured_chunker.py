# TODO: not used in production because chunks do not preserve headings, code blocks, break mid-sentence.
import asyncio
import os
from uuid import UUID

from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.processes.chunker import ChunkerConfig
from unstructured_ingest.v2.processes.connectors.local import (
    LocalConnectionConfig,
    LocalDownloaderConfig,
    LocalIndexerConfig,
    LocalUploaderConfig,
)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig

from src.infrastructure.config.settings import settings
from src.infrastructure.external.supabase_client import supabase_client
from src.infrastructure.storage.data_repository import DataRepository
from src.models.content_models import Document
from src.services.data_service import DataService


class UnstructuredChunker:
    """Class for processing documents using the Unstructured API."""

    def __init__(self, data_service: DataService | None = None):
        self.data_service = data_service

    async def process_documents(self, source_id: UUID) -> None:
        """Process documents in batches for a given source."""
        documents = await self.data_service.get_documents_by_source(source_id)
        self._process_batch(documents)

    def _process_batch(self, documents: list[Document]) -> None:
        """Process a batch of documents using unstructured API."""
        # Create separate directories for input and output
        input_dir = "input_docs"
        output_dir = "output_chunks"
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Save all documents as markdown files
        for doc in documents:
            file_path = f"{input_dir}/{doc.document_id}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(doc.content)

        # Configure and run unstructured pipeline
        pipeline = Pipeline.from_configs(
            context=ProcessorConfig(tqdm=True),
            indexer_config=LocalIndexerConfig(
                input_path=input_dir,
                filename_filter="*.md",  # Only process .md files
            ),
            downloader_config=LocalDownloaderConfig(),
            source_connection_config=LocalConnectionConfig(),
            partitioner_config=PartitionerConfig(
                partition_by_api=True,
                api_key=settings.unstructured_api_key,
                partition_endpoint=settings.unstructured_api_url,
                strategy="auto",
            ),
            chunker_config=ChunkerConfig(
                chunking_strategy="by_title",
                chunk_max_characters=1000,
                chunk_new_after_n_chars=900,
                chunk_overlap=100,
                chunk_combine_text_under_n_chars=150,
            ),
            uploader_config=LocalUploaderConfig(output_dir=output_dir),
        )

        pipeline.run()

    # async def _store_chunks(self, documents: list[Document], output_dir: str) -> None:
    #     """Store chunks for a list of documents."""
    #     # Load chunks from output directory
    #     chunks = []
    #     for doc in documents:
    #         file_path = f"{output_dir}/{doc.document_id}.json"
    #         with open(file_path) as f:
    #             chunks.extend(json.load(f))


async def run_chunker(source_id: UUID) -> None:
    # Initialize Supabase client
    repository = DataRepository(supabase_client)

    # Initialize data service
    data_service = DataService(repository)

    # Initialize the chunker
    chunker = UnstructuredChunker(data_service)

    # Process documents
    await chunker.process_documents(source_id)


if __name__ == "__main__":
    # Define the source_id you want to test with
    source_id = UUID("31a4e0b3-813a-484a-b2d1-86896dd7220e")

    # Run the chunker
    asyncio.run(run_chunker(source_id))
