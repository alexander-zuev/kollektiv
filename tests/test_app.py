from src.generation.claude_assistant import ClaudeAssistant
from src.vector_storage.vector_db import Reranker, ResultRetriever, VectorDB


def test_app_initialization():
    vector_db = VectorDB()
    claude_assistant = ClaudeAssistant(vector_db)
    reranker = Reranker()
    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)

    assert vector_db is not None
    assert claude_assistant is not None
    assert reranker is not None
    assert retriever is not None
