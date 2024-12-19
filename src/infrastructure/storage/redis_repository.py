from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis

from src.infrastructure.common.logger import get_logger
from src.models.chat_models import ConversationHistory, ConversationMessage

logger = get_logger()

T = TypeVar("T", bound=BaseModel)  # T can be any type that is a sub class of BaseModel == all data models


# model[T] == instance of a model
# type[T] == class of a model


class RedisRepository:
    """Asynchronous Redis repository for storing and retrieving data."""

    def __init__(self, client: Redis):
        self.client = client
        self.prefix_config = {
            ConversationHistory: "conversations:{conversation_id}:history",
            ConversationMessage: "conversations:{conversation_id}:pending_messages",
        }
        self.ttl_config = {
            ConversationHistory: 60 * 60 * 24,  # 1 day
            ConversationMessage: 60 * 60,  # 1 hour
        }

    def _get_prefix(self, model_class: type[T], **kwargs: Any) -> str:
        """Get the prefix for the model."""
        try:
            prefix_template = self.prefix_config[model_class]
            logger.debug(f"Prefix template: {prefix_template}")
            return prefix_template.format(**kwargs)
        except KeyError:
            logger.error(f"No key prefix defined for model class: {model_class.__name__}", exc_info=True)
            raise ValueError(f"No key prefix defined for model class: {model_class.__name__}")

    def _get_ttl(self, model_class: type[T]) -> int:
        """Get TTL for the model."""
        try:
            return self.ttl_config[model_class]
        except KeyError:
            raise ValueError(f"No TTL defined for model class: {model_class.__name__}")

    def _to_json(self, model: T) -> str:
        """Convert a model to a JSON string."""
        json_str = model.model_dump_json()
        return json_str

    def _from_json(self, json_str: str, model_class: type[T]) -> T:
        """Convert a JSON string to a model."""
        return model_class.model_validate_json(json_str)

    async def set_method(self, key: UUID, value: T) -> None:
        """Set a value in the Redis database."""
        prefix = self._get_prefix(type(value), conversation_id=key)
        ttl = self._get_ttl(type(value))

        json_str = self._to_json(value)
        await self.client.set(prefix, json_str, ex=ttl)
        logger.info(f"Set {prefix} to {json_str} with expire {ttl}")

    async def get_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Get a value from the Redis database."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        data = await self.client.get(prefix)
        if data is None:
            return None
        return self._from_json(data, model_class)

    async def rpush_method(self, key: UUID, value: T) -> None:
        """Push a value to the end of a list."""
        prefix = self._get_prefix(type(value), conversation_id=key)
        ttl = self._get_ttl(type(value))
        json_str = self._to_json(value)
        await self.client.rpush(prefix, json_str)
        await self.client.expire(prefix, ttl)
        logger.info(f"Rpush {prefix} with expire {ttl}")

    async def lrange_method(self, key: UUID, start: int, end: int, model_class: type[T]) -> list[T]:
        """Retrieve a range of elements from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        items = await self.client.lrange(prefix, start, end)
        return [self._from_json(item, model_class) for item in items]

    async def delete_method(self, key: UUID, model_class: type[T]) -> None:
        """
        Delete a key from the Redis database."""
        prefix = self._get_prefix(model_class=model_class, conversation_id=key)
        await self.client.delete(prefix)
        logger.info(f"Deleted {prefix}")

    async def lpop_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Pop the first element from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        data = await self.client.lpop(prefix)
        if data is None:
            return None
        return self._from_json(data, model_class)

    async def rpop_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Pop the last element from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        data = await self.client.rpop(prefix)
        if data is None:
            return None
        return self._from_json(data, model_class)


# async def test() -> None:
#     client = RedisClient().client
#     redis_repo = RedisRepository(client)

#     conversation_prefix = redis_repo._get_prefix(ConversationHistory, conversation_id=uuid4())
#     message_prefix = redis_repo._get_prefix(ConversationMessage, conversation_id=uuid4())

#     print(conversation_prefix)
#     print(message_prefix)

#     some_key = uuid4()
#     content_block = TextBlock(text="Hello, how are you?")
#     conversation_example = ConversationHistory(
#         conversation_id=some_key,
#         messages=[
#             ConversationMessage(
#                 message_id=some_key,
#                 role=Role.USER,
#                 content=[content_block],
#             )
#         ],
#     )

#     await redis_repo.set_method(some_key, conversation_example)
#     result = await redis_repo.get_method(some_key, ConversationHistory)
#     print(result)

#     message_example = ConversationMessage(
#         message_id=some_key,
#         role=Role.USER,
#         content=[content_block],
#     )
#     message_example2 = ConversationMessage(
#         message_id=some_key,
#         role=Role.ASSISTANT,
#         content=[content_block],
#     )

#     # await redis_repo.rpush_method(some_key, message_example)
#     # await redis_repo.rpush_method(some_key, message_example2)

#     # result = await redis_repo.lrange_method(some_key, 0, -1, ConversationMessage)
#     # print(f"Before delete: {result}")

#     await redis_repo.delete_method(some_key, ConversationMessage)

#     # result = await redis_repo.get_method(some_key, ConversationMessage)
#     # print(f"After delete: {result}")

#     await redis_repo.rpush_method(some_key, message_example)
#     await redis_repo.rpush_method(some_key, message_example2)

#     popped_item = await redis_repo.lpop_method(some_key, ConversationMessage)
#     print(f"After lpop: {popped_item}")

#     result = await redis_repo.lrange_method(some_key, 0, -1, ConversationMessage)
#     print(f"After lpop: {result}")

#     popped_item = await redis_repo.rpop_method(some_key, ConversationMessage)
#     print(f"After rpop: {popped_item}")

#     result = await redis_repo.lrange_method(some_key, 0, -1, ConversationMessage)
#     print(f"After rpop: {result}")


# asyncio.run(test())


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
#     await repo.delete_method("conversations:1:pending_messages", ConversationMessage)


# asyncio.run(test())
