from src.core.chat.claude_assistant import ClaudeAssistant
from src.core.search.vector_db import Reranker, ResultRetriever, VectorDB


def test_app_initialization(mock_openai_embeddings):
    """
    Test the initialization of application components.

    Ensures that instances of VectorDB, ClaudeAssistant, Reranker, and ResultRetriever
    are successfully created and are not None.
    """
    vector_db = VectorDB()
    claude_assistant = ClaudeAssistant(vector_db, api_key="test-key")
    reranker = Reranker()
    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)

    assert vector_db is not None
    assert claude_assistant is not None
    assert reranker is not None
    assert retriever is not None
