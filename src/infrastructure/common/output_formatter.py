from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

ASSISTANT_COLOR = Fore.LIGHTBLUE_EX
USER_COLOR = Fore.GREEN


def print_assistant_stream(message: str, end: str = "\n", flush: bool = True) -> None:
    """
    Print a message in the assistant's color stream.

    Args:
        message (str): The message to be printed.
        end (str, optional): The string appended after the last value, default is a newline.
        flush (bool, optional): Whether to forcibly flush the stream, default is True.

    Returns:
        None

    """
    print(f"{ASSISTANT_COLOR}{message}{Style.RESET_ALL}", end=end, flush=flush)


def print_welcome_message(message: str) -> None:
    """
    Print a welcome message with formatting.

    Args:
        message: The message to print
    """
    print(f"\n{'-' * 80}")
    print(f"{message:^80}")
    print(f"{'-' * 80}\n")


def user_input() -> str:
    """
    Get input from the user with proper formatting.

    Returns:
        str: The user's input as a string
    """
    return input("\nYour input > ").strip()
