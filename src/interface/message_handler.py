import chainlit as cl

from src.interface.command_handler import CommandHandler


class MessageHandler:
    """Handles incoming messages and routes them to appropriate handlers."""

    def __init__(self, claude_assistant, command_handler: CommandHandler):
        self.claude_assistant = claude_assistant
        self.command_handler = command_handler

    async def route_message(self, message: cl.Message):
        """Routes incoming messages to command or regular message handlers."""
        content = message.content.strip()

        if content.startswith("@"):
            await self.handle_command_message(content)
        else:
            await self.handle_regular_message(content)

    async def handle_command_message(self, content: str):
        """Processes command messages and manages multi-step flows."""
        response = await self.command_handler.handle_command(content)
        await cl.Message(content=response).send()

        # Check if we need to start a flow
        if self.command_handler.flow_manager.is_active():
            await self.handle_command_flow()

    async def handle_command_flow(self):
        """Handles the command flow for multi-step inputs."""
        while self.command_handler.flow_manager.is_active():
            prompt = self.command_handler.flow_manager.get_current_prompt()
            user_input = await cl.AskUserMessage(content=prompt).send()

            if user_input:
                result = self.command_handler.process_flow_input(user_input["output"])
                await cl.Message(content=result["response"]).send()

                if result.get("done"):
                    if result.get("final_response"):
                        await cl.Message(content=result["final_response"]).send()
                    break
            else:
                await cl.Message(content="❌ Flow cancelled due to timeout. Please try again.").send()
                self.command_handler.flow_manager.reset()
                break

    async def handle_regular_message(self, content: str):
        """Processes regular messages using the Claude assistant."""
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
