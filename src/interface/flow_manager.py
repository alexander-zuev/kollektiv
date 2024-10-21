class FlowManager:
    """Manages the input flow for collecting required parameters from the user."""

    def __init__(self):
        self.state = None
        self.data = {}

    def reset(self):
        """Resets the state of the flow manager."""
        self.state = None
        self.data = {}

    def start_flow(self, flow_type: str, initial_data: dict):
        """Starts the flow manager."""
        self.reset()
        self.data.update(initial_data)
        if flow_type == "add":
            self.state = "num_pages"

    def get_current_prompt(self) -> str:
        """Gets the current prompt."""
        if self.state == "num_pages":
            return (
                "**Step 1. Enter the maximum number of pages to crawl (default is `25`).**\n"
                "This limits how many pages will be processed from the website.\n\n"
                "*Example:* `35`"
            )
        elif self.state == "exclude_patterns":
            return (
                "**Step 2. Enter URL patterns to exclude, separated by commas (optional).**\n"
                "This helps avoid crawling irrelevant pages. Use path patterns starting with '/' (no domain "
                "needed). \n"
                "Leave empty to crawl all pages.\n\n"
                "*Example:* `/blog/, /archive/, /author/`"
            )
        return ""

    def process_input(self, user_input: str) -> dict:
        """Processes the user input and returns the processed data."""
        if self.state == "num_pages":
            try:
                num_pages = int(user_input) if user_input.strip() else 25
                if num_pages <= 0:
                    return {"response": "Please enter a positive number for maximum pages:", "done": False}
                self.data["num_pages"] = num_pages
                self.state = "exclude_patterns"
                return {"response": self.get_current_prompt(), "done": False}
            except ValueError:
                return {"response": "Please enter a valid number for maximum pages:", "done": False}
        elif self.state == "exclude_patterns":
            patterns = [pattern.strip() for pattern in user_input.split(",")] if user_input.strip() else []
            # Ensure all patterns start with '/'
            patterns = [f"/{pattern.lstrip('/')}" for pattern in patterns]
            self.data["exclude_patterns"] = patterns
            self.state = None
            return {"response": "Processing request...", "done": True}

    def is_active(self) -> bool:
        """Checks if a flow is currently active."""
        return self.state is not None

    def get_data(self) -> dict:
        """Retrieves the collected data when the flow is complete."""
        return self.data
