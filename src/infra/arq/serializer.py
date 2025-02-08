from collections.abc import Callable
from typing import Any

import msgpack

Serializer = Callable[[dict[str, Any]], bytes]
Deserializer = Callable[[bytes], dict[str, Any]]


class MsgpackSerializer:
    """Custom serializer based on msgpack that supports Pydantic models, UUIDs, and other data types out of the box."""

    def __init__(self) -> None:
        # These methods themselves are the callables that ARQ will use
        self.serializer: Serializer = self.default_serializer
        self.deserializer: Deserializer = self.default_deserializer

    def default_serializer(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        return lambda obj: msgpack.packb(obj)

    def default_deserializer(self, data: bytes) -> Any:
        """Deserialize an object from bytes."""
        return lambda data: msgpack.unpackb(data, raw=False)


# Export the serializer and deserializer
_msgpack_serializer = MsgpackSerializer()
serialize = _msgpack_serializer.serializer
deserialize = _msgpack_serializer.deserializer


# Test the serializer
if __name__ == "__main__":
    test_obj = {"name": "John", "age": 30, "city": "New York"}
    serialized = serialize(test_obj)
    deserialized = deserialize(serialized)

    print(deserialized)
    print(type(deserialized))
