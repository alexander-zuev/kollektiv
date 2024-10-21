import re
from urllib.parse import urlparse

from src.interface.flow_manager import FlowManager
from src.kollektiv.manager import Kollektiv
from src.utils.logger import get_logger

logger = get_logger()


class CommandHandler:
    """Handles commands related to document management.

    Attributes:
        kollektiv (Kollektiv): An instance of Kollektiv for document management.
        flow_manager (FlowManager): Manages input flow for multi-step input collection.

    Methods:
        handle_command(command: str) -> str: Handles the input command and performs corresponding actions.
        handle_docs(args: list) -> str: Manages the document-related commands like add, list, and remove.
    """

    def __init__(self, kollektiv: Kollektiv, flow_manager: FlowManager):
        self.kollektiv = kollektiv
        self.flow_manager = flow_manager
        self.commands = {
            "add": "Adds web content to the database. Supports both single and multiple pages.",
            "remove": "Removes web content from the database.",
            "list": "List all content currently loaded into the database.",
        }

    async def handle_command(self, message_content: str) -> str:
        """Main method to handle incoming commands."""
        args = message_content.strip().split()

        if args[0] == "@help":
            return await self.handle_help()
        elif args[0] == "@docs":
            return await self.handle_docs(args[1:])
        else:
            # Catch all other invalid commands starting with @
            return f"Unknown command '{args[0]!r}'. Type `@help` for a list of commands."

    async def handle_help(self) -> str:
        """Returns a help message listing all available commands."""
        help_message = """
        ## Available commands:
        - `@docs add [URL]`: Add a new document or web content.
        - `@docs list`: List all currently loaded documents.
        - `@docs remove [ID]`: Remove a document using its ID.
        - `@help`: Show all available commands.
        """
        return help_message.strip()

    async def handle_docs(self, args: list) -> str:
        """Handles document-related commands such as @docs add, @docs list, and @docs remove.

        Args:
            command_parts (list): The split parts of the command message.

        Returns:
            str: The response message to be sent back to the user.
        """
        if not args:
            return "Invalid @docs command. Type `@help` for usage."

        action = args[0]

        if action == "add":
            return await self.add_web_content(args[1:])
        elif action == "list":
            return self.kollektiv.list_documents()
        elif action == "remove":
            return self.remove_web_content(args[1:])

        return f"Invalid command '@docs {action}'. Type `@help` for usage."

        # if len(command_parts) < 2:
        #     return "Invalid @docs command. Type `@help` for usage."
        #
        # action = command_parts[1]
        #
        # if action == "add":
        #     if len(command_parts) < 3:
        #         return "Usage: `@docs add [URL]`"
        #     url = command_parts[2]
        #     is_valid, processed_url = self.is_valid_url(url)
        #     if not is_valid:
        #         return "Invalid URL provided. Please provide a valid URL."

        #     # Save the URL and start input gathering using FlowManager
        #     self.flow_manager.save_url(processed_url)
        #     prompt = self.flow_manager.start("@docs add")
        #     return prompt
        #
        # elif command_parts[1] == "list":
        #     return self.kollektiv.list_documents()
        #
        # elif command_parts[1] == "remove":
        #     doc_id = command_parts[2] if len(command_parts) > 2 else ""
        #     return self.kollektiv.remove_document(doc_id)
        #
        # return "Invalid command for `@docs`. Type `@help` for usage."

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
        """Initiates the process of adding a document to the collection."""
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

    def process_flow_input(self, user_input: str) -> dict:
        """Processes user input during an active flow."""
        result = self.flow_manager.process_input(user_input)

        if result["done"]:
            flow_data = self.flow_manager.get_data()
            # Validate exclude patterns
            if flow_data.get("exclude_patterns"):
                is_valid, message = self.validate_exclude_patterns(flow_data["exclude_patterns"])
                if not is_valid:
                    return {"response": message, "done": False}

            kollektiv_result = self.kollektiv.add_document(**flow_data)
            return {"response": "Processing complete.", "done": True, "final_response": kollektiv_result}

        return result

    def validate_exclude_patterns(self, patterns: list) -> tuple[bool, str]:
        """Validates excluded patterns for correctness."""
        invalid_patterns = [p for p in patterns if not p.startswith("/")]
        if invalid_patterns:
            return False, f"Invalid patterns: {', '.join(invalid_patterns)}. All patterns must start with '/'."
        return True, "Patterns are valid."
