from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from redis.asyncio import Redis as AsyncRedis

from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.models.chat_models import ConversationHistory, ConversationMessage

logger = get_logger()

T = TypeVar("T", bound=BaseModel)  # T can be any type that is a sub class of BaseModel == all data models


# model[T] == instance of a model
# type[T] == class of a model


class RedisRepository:
    """Asynchronous Redis repository for storing and retrieving data."""

    def __init__(self, manager: RedisManager):
        self.manager = manager
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
        json_str = model.model_dump_json(by_alias=True, serialize_as_any=True)
        return json_str

    def _from_json(self, json_str: str, model_class: type[T]) -> T:
        """Convert a JSON string to a model."""
        # logger.debug(_truncate_message(f"From JSON: {json_str}"))
        result = model_class.model_validate_json(json_str)
        return result

    async def create_pipeline(self, transaction: bool = True) -> AsyncRedis:
        """Create a new pipeline"""
        client = await self.manager.get_async_client()
        return client.pipeline(transaction=transaction)

    async def set_method(self, key: UUID, value: T, pipe: AsyncRedis | None = None) -> None:
        """Set a value in the Redis database, optionally as part of pipeline."""
        prefix = self._get_prefix(type(value), conversation_id=key)
        ttl = self._get_ttl(type(value))
        json_str = self._to_json(value)

        if pipe:
            pipe.set(prefix, json_str, ex=ttl)
            logger.debug(f"Added SET operation to pipeline for key: {prefix}")
        else:
            client = await self.manager.get_async_client()
            await client.set(prefix, json_str, ex=ttl)
            logger.debug(f"Set Redis key: {prefix} (TTL: {ttl}s), data: {json_str}")

    async def get_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Get a value from the Redis database."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        client = await self.manager.get_async_client()
        data = await client.get(prefix)
        if data is None:
            logger.debug(f"Key not found in Redis: {prefix}")
            return None
        return self._from_json(data, model_class)

    async def rpush_method(self, key: UUID, value: T) -> None:
        """Push a value to the end of a list."""
        prefix = self._get_prefix(type(value), conversation_id=key)
        ttl = self._get_ttl(type(value))
        json_str = self._to_json(value)
        client = await self.manager.get_async_client()
        await client.rpush(prefix, json_str)
        await client.expire(prefix, ttl)
        logger.info(f"Pushed to Redis list: {prefix} (TTL: {ttl}s)")

    async def lrange_method(self, key: UUID, start: int, end: int, model_class: type[T]) -> list[T]:
        """Retrieve a range of elements from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        client = await self.manager.get_async_client()
        items = await client.lrange(prefix, start, end)
        return [self._from_json(item, model_class) for item in items]

    async def delete_method(self, key: UUID, model_class: type[T], pipe: AsyncRedis | None = None) -> None:
        """Delete a key from the Redis database."""
        prefix = self._get_prefix(model_class=model_class, conversation_id=key)
        if pipe:
            pipe.delete(prefix)
            logger.debug(f"Added delete to pipeline: {prefix}")
        else:
            client = await self.manager.get_async_client()
            await client.delete(prefix)
            logger.info(f"Deleted from Redis: {prefix}")

    async def lpop_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Pop the first element from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        client = await self.manager.get_async_client()
        data = await client.lpop(prefix)
        if data is None:
            return None
        return self._from_json(data, model_class)

    async def rpop_method(self, key: UUID, model_class: type[T]) -> T | None:
        """Pop the last element from a list."""
        prefix = self._get_prefix(model_class, conversation_id=key)
        client = await self.manager.get_async_client()
        data = await client.rpop(prefix)
        if data is None:
            return None
        return self._from_json(data, model_class)
