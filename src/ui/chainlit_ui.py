import chainlit as cl

from src.generation.claude_assistant import ClaudeAssistant


@cl.on_chat_start
async def on_chat_start():
    """Handler for chat start event."""
    await cl.Message(content="Welcome to OmniClaude! How can I assist you today?").send()


@cl.on_message
async def handle_message(message, claude_assistant: ClaudeAssistant, stream: bool = True):
    """Handler for incoming messages."""

    if not claude_assistant:
        await cl.Message(content="Assistant is not initialized. Please try again later.").send()
        return

    try:
        response_stream = claude_assistant.get_response(message.content, stream=stream)

        async for event in response_stream:
            if event["type"] == "text":
                await cl.Message(content=event["content"]).send()
            elif event["type"] == "tool_use":
                tool_name = event.get("tool", "Unknown Tool")
                await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
    except Exception as e:
        await cl.Message(content=f"An error occurred: {str(e)}").send()


def run_chainlit(assistant: ClaudeAssistant, stream: bool = True):
    handle_message(message=None, claude_assistant=assistant, stream=stream)
