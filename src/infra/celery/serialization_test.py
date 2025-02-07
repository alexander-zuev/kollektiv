from uuid import uuid4

from src.models.content_models import Chunk

sample_chunk = Chunk(
    chunk_id=uuid4(),
    source_id=uuid4(),
    text="This is a test chunk",
    headers={"test": "test"},
    document_id=uuid4(),
    token_count=100,
    page_title="Test Page",
    page_url="https://test.com",
)

serialized_chunk = sample_chunk.model_dump(mode="json")
print(f"Serialized chunk with mode='json': {serialized_chunk}")
print(f"Accessing as an object: {serialized_chunk['headers']}")

print()
serialized_json = sample_chunk.model_dump_json()
print(f"Serialized chunk with model_dump_json: {serialized_json}")
print(f"Accessing as an object: {serialized_json['headers']}")

print()
deserialized_chunk = Chunk.model_validate(serialized_chunk)
print(f"Headers type: {type(deserialized_chunk.headers)} and value: {deserialized_chunk.headers}")
deserialized_chunk_json = Chunk.model_validate_json(serialized_json)
print(f"Headers type: {type(deserialized_chunk_json.headers)} and value: {deserialized_chunk_json.headers}")
