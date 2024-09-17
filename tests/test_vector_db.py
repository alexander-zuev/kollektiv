from src.vector_storage.vector_db import DocumentProcessor, VectorDB


def test_vector_db_initialization():
    vector_db = VectorDB()
    assert vector_db is not None
    assert vector_db.collection_name == "local-collection"


def test_document_processor_initialization():
    processor = DocumentProcessor("test_file.json")
    assert processor is not None
    assert processor.file_name == "test_file.json"
