import importlib
from collections.abc import Callable
from datetime import date, datetime, time
from functools import lru_cache
from typing import Any
from uuid import UUID

import msgpack
from pydantic import BaseModel

from src.infra.logger import get_logger

logger = get_logger()

# The serializer type: takes a dictionary and returns bytes
Serializer = Callable[[dict[str, Any]], bytes]
# The deserializer type: takes bytes and returns a dictionary
Deserializer = Callable[[bytes], dict[str, Any]]


@lru_cache(maxsize=128)
def get_model_class(qualified_name: str) -> type[BaseModel]:
    """Get Pydantic model class from its fully qualified name."""
    try:
        module_name, class_name = qualified_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        model_cls = getattr(module, class_name)

        if not issubclass(model_cls, BaseModel):
            raise ValueError(f"Class {qualified_name} is not a Pydantic model")

        return model_cls
    except Exception as e:
        logger.error(f"Failed to load model {qualified_name}: {str(e)}")
        raise


class MsgpackSerializer:
    """Custom serializer based on msgpack that supports Pydantic models, UUIDs, and other types.

    Features:
    - Handles Pydantic models via dynamic class loading
    - Supports UUIDs, lists, tuples, and nested dictionaries
    - Provides safe fallbacks for failed model reconstruction
    - Uses msgpack for efficient binary serialization
    """

    def __init__(self) -> None:
        self.serializer: Serializer = self._serialize
        self.deserializer: Deserializer = self._deserialize

    def _get_model_reference(self, obj: BaseModel) -> str:
        """Get fully qualified reference for a Pydantic model."""
        model_reference = f"{obj.__class__.__module__}.{obj.__class__.__qualname__}"
        logger.debug(f"Model reference: {model_reference}")
        return model_reference

    def _normalize(self, obj: Any) -> Any:
        """Convert objects to msgpack-serializable format."""
        if isinstance(obj, BaseModel):
            return {"__pydantic__": self._get_model_reference(obj), "data": obj.model_dump(mode="json")}
        elif isinstance(obj, UUID):
            return {"__uuid__": str(obj)}
        elif isinstance(obj, datetime):
            return {
                "__datetime_type__": "datetime",
                "__value__": obj.isoformat(),
                "__tzinfo__": obj.tzinfo is not None,
            }
        elif isinstance(obj, date):
            return {
                "__datetime_type__": "date",
                "__value__": obj.isoformat(),
            }
        elif isinstance(obj, time):
            return {
                "__datetime_type__": "time",
                "__value__": obj.isoformat(),
            }
        elif isinstance(obj, (list, tuple)):
            return [self._normalize(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(key): self._normalize(value) for key, value in obj.items()}
        return obj

    def _denormalize(self, obj: Any) -> Any:
        """Reconstruct objects from msgpack-serialized format."""
        if isinstance(obj, dict):
            if "__pydantic__" in obj:
                try:
                    model_cls = get_model_class(obj["__pydantic__"])
                    return model_cls.model_validate(obj["data"])
                except Exception as e:
                    logger.error(f"Failed to reconstruct model: {str(e)}")
                    return obj["data"]
            elif "__uuid__" in obj:
                return UUID(obj["__uuid__"])
            elif "__datetime_type__" in obj:
                type_name = obj["__datetime_type__"]
                value = obj["__value__"]
                if type_name == "datetime":
                    dt = datetime.fromisoformat(value)
                    return dt if obj["__tzinfo__"] else dt.replace(tzinfo=None)
                elif type_name == "date":
                    return date.fromisoformat(value)
                elif type_name == "time":
                    return time.fromisoformat(value)
            else:
                return {key: self._denormalize(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._denormalize(item) for item in obj]
        return obj

    def _serialize(self, obj: dict[str, Any]) -> bytes:
        """Serialize to msgpack bytes."""
        logger.debug(f"Serializing object: {obj} with type: {type(obj)}")
        return msgpack.packb(self._normalize(obj))

    def _deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize from msgpack bytes."""
        deserialized = self._denormalize(msgpack.unpackb(data, raw=False))
        logger.debug(f"Deserialized object: {deserialized} with type: {type(deserialized)}")
        return deserialized


# Export the serializer and deserializer
_msgpack_serializer = MsgpackSerializer()
serialize = _msgpack_serializer.serializer
deserialize = _msgpack_serializer.deserializer


# Comprehensive test suite
if __name__ == "__main__":
    from uuid import uuid4

    from src.models.content_models import Chunk, Document, DocumentMetadata, ProcessingEvent

    def test_serialization(obj: Any, name: str) -> None:
        """Test serialization/deserialization of an object and print results."""
        print(f"\nTesting {name}:")
        print(f"Original: {obj}")

        serialized = serialize({"data": obj})
        deserialized = deserialize(serialized)

        print(f"Deserialized: {deserialized['data']}")
        print(f"Types match: {type(obj) == type(deserialized['data'])}")
        print("-" * 50)

    # Test 1: Simple Pydantic Model
    doc = Document(
        document_id=uuid4(),
        source_id=uuid4(),
        content="Hello, world!",
        metadata=DocumentMetadata(source_url="https://example.com"),
    )
    test_serialization(doc, "Simple Pydantic Model (Document)")

    # Test 2: UUID
    test_id = uuid4()
    test_serialization(test_id, "UUID")

    # Test 3: List with mixed types
    mixed_list = [uuid4(), doc, {"nested": "dict"}, [1, 2, 3]]
    test_serialization(mixed_list, "Mixed List")

    # Test 4: Dictionary with mixed types
    mixed_dict = {"uuid": uuid4(), "model": doc, "list": [1, 2, 3], "nested": {"key": "value"}}
    test_serialization(mixed_dict, "Mixed Dictionary")

    # Test 5: Nested Pydantic Models
    chunk = Chunk(
        chunk_id=uuid4(),
        document_id=doc.document_id,
        source_id=doc.document_id,
        text="Chunk content",
        token_count=100,
        page_title="Test Page",
        page_url="https://example.com",
        headers={"Content-Type": "text/plain"},
    )
    test_serialization(chunk, "Nested Model (Chunk)")

    # Test 6: Complex nested structure
    complex_obj = {
        "document": doc,
        "chunks": [chunk, chunk],
        "metadata": {"ids": [uuid4(), uuid4()], "nested_doc": doc},
    }
    test_serialization(complex_obj, "Complex Nested Structure")

    # Test 7: Event with metadata
    event = ProcessingEvent(
        source_id=uuid4(),
        event_type="processing",
        metadata={"status": "complete"},
    )
    test_serialization(event, "Event with Metadata")
