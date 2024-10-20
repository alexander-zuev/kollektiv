import chainlit as cl

from src.interface.command_handler import CommandHandler


class MessageHandler:
    """Message handler class."""

    def __init__(self, claude_assistant, command_handler: CommandHandler):
        self.claude_assistant = claude_assistant
        self.command_handler = command_handler

    async def handle_message(self, message: cl.Message):
        """Handles incoming message."""
        if message.content.startswith("@"):
            response = await self.command_handler.handle_command(message.content)
            await cl.Message(content=response).send()
        else:
            await self.handle_regular_message(message.content)

    async def handle_regular_message(self, content: str):
        """Handles incoming regular message."""
        response = self.claude_assistant.get_response(user_input=content, stream=True)

        current_message = cl.Message(content="")
        await current_message.send()

        tool_used = False

        for event in response:
            if event["type"] == "text":
                if tool_used:
                    # If a tool was used, start a new message for the assistant's response
                    current_message = cl.Message(content="")
                    await current_message.send()
                    tool_used = False
                await current_message.stream_token(event["content"])
            elif event["type"] == "tool_use":
                tool_name = event.get("tool", "Unknown tool")
                await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
                tool_used = True

        await current_message.update()
