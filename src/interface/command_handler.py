from src.kollektiv.manager import Kollektiv


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

    def handle_command(self, command: str) -> str:
        """Handles the input command and performs corresponding actions."""
        parts = command.split()
        if len(parts) < 2 or parts[0] != "@docs":
            return "Invalid command. Use @docs [add|remove|list] [args]"

        action = parts[1]
        if action == "add":
            return self.add_document(parts[2:])
        elif action == "remove":
            return self.remove_document(parts[2:])
        elif action == "list":
            return self.list_documents()
        else:
            return f"Unknown command: {action}"

    def add_document(self, args: list) -> str:
        """Adds a document to the collection."""
        if not args:
            return "Missing URL. Usage: @docs add [URL]"
        url = args[0]
        return self.kollektiv.add_document(url)

    def remove_document(self, args: list) -> str:
        """Removes a document from the collection."""
        if not args:
            return "Missing document ID. Usage: @docs remove [ID]"
        doc_id = args[0]
        return self.kollektiv.remove_document(doc_id)

    def list_documents(self) -> str:
        """Lists all documents in the collection."""
        return self.kollektiv.list_documents()
