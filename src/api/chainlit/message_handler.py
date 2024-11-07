import logging

import chainlit as cl
from chainlit.message import Message

from src.api.chainlit.command_handler import CommandHandler
from src.core.chat.claude_assistant import ClaudeAssistant

logger = logging.getLogger(__name__)


# TODO: Different types of replies: AssistantMessage, SystemMessage (success/error/warning)
class MessageHandler:
    """Handles message processing and routing in the chat interface."""

    def __init__(self) -> None:
        """Initialize the message handler."""
        self.claude_assistant: ClaudeAssistant | None = None
        self.command_handler: CommandHandler | None = None

    @staticmethod
    def create(
        claude_assistant: ClaudeAssistant | None = None, command_handler: CommandHandler | None = None
    ) -> "MessageHandler":
        """Create a new MessageHandler instance with optional components."""
        handler = MessageHandler()
        handler.claude_assistant = claude_assistant
        handler.command_handler = command_handler
        return handler

    async def route_message(self, message: Message) -> None:
        """Routes incoming messages to command or regular message handlers."""
        content = message.content.strip()

        if content.startswith("@"):
            await self.handle_command_message(content)
        else:
            await self.handle_regular_message(content)

    async def handle_command_message(self, content: str) -> None:
        """Processes command messages and manages multi-step flows."""
        try:
            response = await self.command_handler.handle_command(content)
            await cl.Message(content=response).send()

            # Check if we need to start a flow
            if self.command_handler.flow_manager.is_active():
                await self.handle_command_flow()
        except Exception as e:
            logger.error(f"Command handling error: {e}")
            await cl.Message(content=f"❌ Error processing command: {str(e)}").send()

    async def handle_command_flow(self) -> None:
        """Handles the command flow for multi-step inputs."""
        while self.command_handler.flow_manager.is_active():
            prompt = self.command_handler.flow_manager.get_current_prompt()
            user_input = await cl.AskUserMessage(content=prompt).send()

            if isinstance(user_input, dict) and "output" in user_input:
                result = await self.command_handler.process_flow_input(user_input["output"])
                await cl.Message(content=result["response"]).send()

                if result.get("done"):
                    if result.get("final_response"):
                        await cl.Message(content=result["final_response"]).send()
                    break
            else:
                await cl.Message(content="❌ Flow cancelled due to timeout. Please try again.").send()
                self.command_handler.flow_manager.reset()
                break

    async def handle_regular_message(self, content: str) -> None:
        """
        Processes regular messages using the Claude assistant.

        Args:
            content: The message content to process.

        Returns:
            None
        """
        if not self.claude_assistant:
            await cl.Message(content="❌ Assistant not initialized").send()
            return

        response = self.claude_assistant.get_response(user_input=content, stream=True)

        current_message = Message(content="")
        await current_message.send()

        tool_used = False

        for event in response:
            if event["type"] == "text":
                if tool_used:
                    # If a tool was used, start a new message for the assistant's response
                    current_message = Message(content="")
                    await current_message.send()
                    tool_used = False
                await current_message.stream_token(event["content"])
            elif event["type"] == "tool_use":
                tool_name = event.get("tool", "Unknown tool")
                await cl.Message(content=f"🛠️ Using {tool_name} tool.").send()
                tool_used = True

        await current_message.update()
