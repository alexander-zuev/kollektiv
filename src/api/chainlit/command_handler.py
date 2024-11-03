import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from src.api.client.api_client import KollektivAPIClient
from src.api.v0.content.schemas import (
    AddContentSourceRequest,
    ContentSourceConfig,
    ContentSourceType,
)
from src.core.chat.flow_manager import UserInputManager
from src.infrastructure.config.logger import get_logger

if TYPE_CHECKING:
    from src.services.manager import Kollektiv

logger = get_logger()


class CommandHandler:
    """Handles commands related to document management."""

    def __init__(
        self,
        kollektiv: "Kollektiv",  # Keep for now
        flow_manager: UserInputManager,
    ):
        """Initialize command handler.

        Args:
            kollektiv: Kollektiv instance for legacy operations
            flow_manager: Manages input flow for multi-step input collection
        """
        self.kollektiv = kollektiv  # Keep for now - used by list/remove
        self.flow_manager = flow_manager
        self.api_client = KollektivAPIClient()

    async def handle_command(self, message_content: str) -> str:
        """Main method to handle incoming commands."""
        args = message_content.strip().split()

        if args[0] == "@help":
            return await self.handle_help_command()
        elif args[0] == "@docs":
            return await self.handle_docs_command(args[1:])
        else:
            # Catch all other invalid commands starting with @
            return f"Unknown command '{args[0]!r}'. Type `@help` for a list of commands."

    async def handle_help_command(self) -> str:
        """Returns a help message listing all available commands."""
        help_message = """
        ## Available commands:
        - `@docs add [URL]`: Add a new document or web content.
        - `@docs list`: List all currently loaded documents.
        - `@docs remove [ID]`: Remove a document using its ID.
        - `@help`: Show all available commands.
        """
        return help_message.strip()

    async def handle_docs_command(self, command_parts: list) -> str:
        """Handles document-related commands such as @docs add, @docs list, and @docs remove.

        Args:
            command_parts: The split parts of the command message.

        Returns:
            str: The response message to be sent back to the user.
        """
        if not command_parts:
            return "Invalid @docs command. Type `@help` for usage."

        action = command_parts[0]

        if action == "add":
            return await self.add_web_content(command_parts[1:])
        elif action == "list":
            return self.kollektiv.list_documents()  # Keep using Kollektiv for now
        elif action == "remove":
            return self.kollektiv.remove_document(command_parts[1])  # Keep using Kollektiv for now

        return f"Invalid command '@docs {action}'. Type `@help` for usage."

    def is_valid_url(self, url: str) -> tuple[bool, str]:
        """Validates the provided URL using most common sense patterns. Removes ip addresses, ports and invalid URLs."""
        # If no scheme is provided, prepend 'https://'
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                # Basic format check using regex
                pattern = re.compile(
                    r"^(https?:\/\/)?(www\.)?"  # Optional scheme and www
                    r"[\w\.-]+\."  # Domain name
                    r"[a-z]{2,}"  # TLD
                    r"(\/\S*)?$",  # Optional path and query parameters
                    re.IGNORECASE,
                )
                if pattern.match(url):
                    return True, url
        except Exception as e:
            logger.error(f"Error parsing URL: {str(e)}")

        return False, url

    async def add_web_content(self, args: list) -> str:
        """Initiates the process of adding web content.

        Args:
            args: List of command arguments, first should be URL

        Returns:
            str: Response message indicating process started or error
        """
        if not args:
            return (
                "No URL provided. Please ensure you include a valid URL - @docs add [URL]\n"
                "Accepted formats:\n"
                "- https://www.example.com\n"
                "- www.example.com\n"
                "- example.com"
            )

        url = args[0]
        is_valid, processed_url = self.is_valid_url(url)

        if not is_valid:
            return "Invalid URL..."

        # Start the flow with the URL
        self.flow_manager.start_flow("add", {"url": processed_url})
        return f"Starting the process to add web content for **{processed_url}**."

    def remove_web_content(self, args: list) -> str:
        """Removes a document from the collection."""
        logger.info(f"Attempting to remove web content with args: {args}")
        if not args:
            return "Missing document ID. Usage: @docs remove [ID]\nExample: @docs remove 123"
        doc_id = args[0]
        return self.kollektiv.remove_document(doc_id)

    def list_synced_web_content(self) -> str:
        """Lists all documents in the collection."""
        logger.info("Listing synced web content")
        return self.kollektiv.list_documents()

    async def process_flow_input(self, user_input: str) -> dict:
        """Process user input during flow."""
        result = self.flow_manager.process_input(user_input)

        if result["done"]:
            flow_data = self.flow_manager.get_data()
            try:
                # Create request using flow data
                request = AddContentSourceRequest(
                    type=ContentSourceType.WEB,
                    name=f"Content from {flow_data['url']}",
                    url=flow_data["url"],
                    config=ContentSourceConfig(
                        max_pages=flow_data["num_pages"],
                        exclude_sections=flow_data["exclude_patterns"],
                    ),
                )

                # Use API client instead of direct service call
                source = await self.api_client.add_source(request)

                return {
                    "response": "Processing started",
                    "done": True,
                    "final_response": (
                        f"Content source added with ID: {source.id}\n"
                        f"Status: {source.status}\n"
                        f"Max Pages: {source.config.max_pages}\n"
                        f"Excluded Sections: {', '.join(source.config.exclude_sections) or 'None'}"
                    ),
                }
            except Exception as e:
                logger.error(f"Failed to add content: {e}")
                return {"response": f"Failed to add content: {str(e)}", "done": True}

        return result

    def validate_exclude_patterns(self, patterns: list) -> tuple[bool, str]:
        """Validates excluded patterns for correctness."""
        invalid_patterns = [p for p in patterns if not p.startswith("/")]
        if invalid_patterns:
            return False, f"Invalid patterns: {', '.join(invalid_patterns)}. All patterns must start with '/'."
        return True, "Patterns are valid."

    async def cleanup(self) -> None:
        """Cleanup resources when command handler is done."""
        if hasattr(self, "api_client"):
            await self.api_client.close()
