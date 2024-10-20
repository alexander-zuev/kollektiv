import re
from urllib.parse import urlparse

from src.kollektiv.manager import Kollektiv
from src.utils.logger import get_logger

logger = get_logger()


class CommandHandler:
    """Handles commands related to document management.

    Attributes:
        kollektiv (Kollektiv): An instance of Kollektiv for document management.

    Methods:
        handle_command(command: str) -> str: Handles the input command and performs corresponding actions.
        add_document(args: list) -> str: Adds a document to the collection.
        remove_document(args: list) -> str: Removes a document from the collection.
        list_documents() -> str: Lists all documents in the collection.
    """

    def __init__(self, kollektiv: Kollektiv):
        self.kollektiv = kollektiv
        self.commands = {
            "add": "Adds web content to the database. Supports both single and multiple pages.",
            "remove": "Removes web content from the database.",
            "list": "List all content currently loaded into the database.",
        }

    async def handle_command(self, message_content: str) -> str:
        """Main method to handle incoming commands."""
        command_parts = message_content.strip().split()

        if command_parts[0] == "@help":
            return await self.handle_help()
        elif command_parts[0] == "@docs":
            return await self.handle_docs(command_parts)
        else:
            # Catch all other invalid commands starting with @
            return f"Unknown command '{command_parts[0]!r}'. Type `@help` for a list of commands."

    async def handle_help(self) -> str:
        """Returns a help message listing all available commands."""
        help_message = """
        Available commands:
        - `@docs add [URL]`: Add a new document or web content.
        - `@docs list`: List all currently loaded documents.
        - `@docs remove [ID]`: Remove a document using its ID.
        - `@help`: Show all available commands.
        """
        return help_message.strip()

    async def handle_docs(self, command_parts: list) -> str:
        """Handles @docs commands such as add, remove, list."""
        if len(command_parts) < 2:
            return "Invalid usage. Usage:\n`@docs add [URL]`\n`@docs list`\n`@docs remove [ID]`"

        command = command_parts[1]
        if command == "add":
            return self.add_web_content(command_parts[2:])
        elif command == "remove":
            return self.remove_web_content(command_parts[2:])
        elif command == "list":
            return self.list_synced_web_content()
        else:
            return "Invalid command for `@docs`. Type `@help` for usage."

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

    def add_web_content(self, args: list) -> str:
        """Adds a document to the collection."""
        logger.info(f"Attempting to add web content with args: {args}")
        if not args:
            return (
                "No URL was provided. Please ensure you include a valid URL - @docs add [URL]\n"
                "Accepted formats:\n"
                "- https://www.example.com\n"
                "- www.example.com\n"
                "- example.com"
            )
        url = args[0]
        is_valid, processed_url = self.is_valid_url(url)

        if not is_valid:
            return (
                f"Invalid URL provided: {url}\n"
                "Please provide a valid URL in one of the following formats:\n"
                "- https://www.example.com\n"
                "- www.example.com\n"
                "- example.com"
            )

        # Provide immediate feedback
        feedback = f"Starting to add content from {url}. This may take a few moments..."
        logger.info(feedback)

        # Here you would typically start an asynchronous task to add the document
        # For now, we'll just call the synchronous method
        result = self.kollektiv.add_document(url)
        return result

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
