# TODO: redo from scratch
from src.core.search.vector_db import DocumentProcessor, VectorDB


def test_vector_db_initialization(mock_openai_embeddings):
    """
    Test the initialization of the VectorDB class.

    Ensures that an instance of VectorDB is created and the collection_name
    is set to the default value "local-collection".

    Returns:
        bool: True if the tests pass, otherwise raises an assertion error.
    """
    vector_db = VectorDB()
    assert vector_db is not None
    assert vector_db.collection_name == "local-collection"


def test_document_processor_initialization():
    """
    Test the initialization of the DocumentProcessor class.

    Checks whether an instance of DocumentProcessor is successfully created
    and is not None.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If the DocumentProcessor instance is None.
    """
    processor = DocumentProcessor()
    assert processor is not None
