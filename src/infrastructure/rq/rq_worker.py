from src.core.content.chunker import Chunker
from src.core.search.vector_db import VectorDB
from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.chroma_client import ChromaClient
from src.infrastructure.job_manager import JobManager

logger = get_logger()


class RQWorker:
    """Customer RQ worker class with the necessary dependencies."""

    def __init__(
        self,
        chunker: Chunker | None = None,
        chroma_client: ChromaClient | None = None,
        vector_db: VectorDB | None = None,
        job_manager: JobManager | None = None,
    ):
        """Initialize RQWorker with the necessary dependencies."""
        self.chunker = Chunker()
        self.chroma_client = ChromaClient().create_client()
        self.vector_db = VectorDB(chroma_client=self.chroma_client)
        self.job_manager = JobManager()
