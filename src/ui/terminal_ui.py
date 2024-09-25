from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger
from src.utils.output_formatter import print_assistant_message

logger = get_logger()


@base_error_handler
def run_terminal_ui(claude_assistant):
    print("Welcome to OmniClaude! How can I assist you today?")
    while True:
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            break

        stream = True
        response = claude_assistant.get_response(user_message, stream=stream)
        print_assistant_message("OmniClaude: ", end="")
        if stream:
            for event in response:
                if event["type"] == "text":
                    print(event["content"], end="", flush=True)
                elif event["type"] == "tool_use":
                    print(f"\nUsing {event['tool']} tool 🧰.\n", end="", flush=True)
            print()  # Add a newline after the complete response
        else:
            print(response)
