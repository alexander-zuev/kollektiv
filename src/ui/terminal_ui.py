from src.utils.decorators import application_level_handler
from src.utils.logger import get_logger
from src.utils.output_formatter import print_assistant_stream, print_welcome_message, user_input

logger = get_logger()


@application_level_handler
def run_terminal_ui(claude_assistant):
    print_welcome_message("Welcome to OmniClaude! How can I assist you today?")
    while True:
        print()  # new line before user input
        user_message = user_input()
        if user_message.lower() in ["exit", "quit"]:
            break

        print()  # new line before assistant message
        stream = True
        response = claude_assistant.get_response(user_message, stream=stream)
        print_assistant_stream("OmniClaude: ", end="")
        if stream:
            for event in response:
                if event["type"] == "text":
                    print(event["content"], end="", flush=True)
                elif event["type"] == "tool_use":
                    print_assistant_stream(f"\nUsing {event['tool']} tool 🧰.\n")
                    # print(f"\nUsing {event['tool']} tool 🧰.\n", end="", flush=True)
            print()  # Add a newline after the complete response
        else:
            print(response)
