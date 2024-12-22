from pydantic import BaseModel

from src.models.chat_models import ConversationHistory, ConversationMessage, Role, TextBlock, ToolUseBlock


def serialize_model(model: BaseModel) -> dict:
    """Serialize a message to a dictionary."""
    return model.model_dump(serialize_as_any=True)


def serialize_json(model: BaseModel) -> str:
    """Serialize a message to a JSON string."""
    return model.model_dump_json(serialize_as_any=True)


message = ConversationMessage(role=Role.USER, content=[TextBlock(text="Hello, world!")])
message_tool = ConversationMessage(
    role=Role.ASSISTANT,
    content=[ToolUseBlock(name="tool_name", input={"key": "value"}, id="tool_use_id")],
)
history = ConversationHistory(messages=[message, message_tool])
# print(f"serialize_model(message): {serialize_model(message)}")
# print(f"serialize_json(message): {serialize_json(message)}")


print(f"history.to_anthropic_messages(): {history.to_anthropic_messages()}")
# print(f"serialize_json(history): {serialize_json(history)}")
# print(f"serialize_model(history): {serialize_model(history)}")
