import asyncio
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel
from redis.asyncio import Redis

from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.redis_client import RedisClient
from src.models.chat_models import ConversationHistory, ConversationMessage, Role, TextBlock

logger = get_logger()

T = TypeVar("T", bound=BaseModel)  # T can be any type that is a sub class of BaseModel == all data models


# model[T] == instance of a model
# type[T] == class of a model


class RedisRepository:
    """Asynchronous Redis repository for storing and retrieving data."""

    def __init__(self, client: Redis):
        self.client = client
        self.conversation_prefix = "conversations:{conversation_id}:history"
        self.message_prefix = "conversations:{conversation_id}:pending_messages"
        self.conversation_ttl = 60 * 60 * 24  # 1 day
        self.message_ttl = 60 * 60  # 1 hour

    def _to_json(self, model: T) -> str:
        """Convert a model to a JSON string."""
        json_str = model.model_dump_json()
        return json_str

    def _from_json(self, json_str: str, model_class: type[T]) -> T:
        """Convert a JSON string to a model."""
        return model_class.model_validate_json(json_str)

    async def set_method(self, key: str, value: T) -> None:
        """Set a value in the Redis database."""
        json_str = self._to_json(value)
        await self.client.set(key, json_str, ex=self.conversation_ttl)
        logger.info(f"Set {key} to {json_str} with expire {self.conversation_ttl}")

    async def get_method(self, key: str, model_class: type[T]) -> T | None:
        """Get a value from the Redis database."""
        data = await self.client.get(key)
        if data is None:
            return None
        return self._from_json(data, model_class)

    async def rpush_method(self, key: str, value: T) -> None:
        """Push a value to the end of a list."""
        json_str = self._to_json(value)
        await self.client.rpush(key, json_str)
        await self.client.expire(key, self.message_ttl)
        logger.info(f"Rpush {key} with expire {self.message_ttl}")

    async def lrange_method(self, key: str, start: int, end: int, model_class: type[T]) -> list[T]:
        """Retrieve a range of elements from a list."""
        items = await self.client.lrange(key, start, end)
        return [self._from_json(item, model_class) for item in items]

    async def delete_method(self, key: str) -> None:
        """Delete a key from the Redis database."""
        await self.client.delete(key)
        logger.info(f"Deleted {key}")

    async def lpop_method(self, key: str, model_class: type[T]) -> T | None:
        """Pop the first element from a list."""
        data = await self.client.lpop(key)
        if data is None:
            return None
        return self._from_json(data.decode("utf-8"), model_class)

    async def rpop_method(self, key: str, model_class: type[T]) -> T | None:
        """Pop the last element from a list."""
        data = await self.client.rpop(key)
        if data is None:
            return None
        return self._from_json(data.decode("utf-8"), model_class)


# uuid = uuid4()
# content_block = TextBlock(text="Hello, how are you?")
# conversation_example = ConversationHistory(
#     conversation_id=str(uuid),
#     messages=[
#         ConversationMessage(
#             message_id=str(uuid),
#             role=Role.USER,
#             content=[content_block],
#         )
#     ],
# )

# message_example = ConversationMessage(
#     message_id=str(uuid),
#     role="user",
#     content=[content_block],
# )
# message_example_2 = ConversationMessage(
#     message_id=str(uuid),
#     role="assistant",
#     content=[content_block],
# )
# pending_list = [message_example, message_example_2]


# async def test() -> None:
#     """Test the Redis repository."""
#     client = RedisClient().client
#     repo = RedisRepository(client)

#     # Checking saving
#     # json_str = repo._to_json(conversation_example)
#     # print("From model:", json_str)

#     # await repo.set_method("conversations:1:history", conversation_example)
#     # result = await repo.get_method("conversations:1:history", ConversationHistory)
#     # print("From redis:", result)

#     await repo.rpush_method("conversations:1:pending_messages", message_example)
#     await repo.rpush_method("conversations:1:pending_messages", message_example_2)
#     result = await repo.lrange_method("conversations:1:pending_messages", 0, -1, ConversationMessage)
#     for message in result:
#         print(f"Message: {message.model_dump_json()}")
#     await repo.delete_method("conversations:1:pending_messages")


# asyncio.run(test())
