from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

ASSISTANT_COLOR = Fore.LIGHTBLUE_EX
USER_COLOR = Fore.GREEN


def print_assistant_stream(message: str, end: str = "\n", flush: bool = True):
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


def print_welcome_message(message: str):
    """
    Print the welcome message to the console.

    Args:
        message (str): The welcome message to be printed.

    Returns:
        None

    """
    print(f"\n{ASSISTANT_COLOR}{message}{Style.RESET_ALL}")


def user_input():
    """
    Prompt the user for input and return the input string.

    Args:
        None

    Returns:
        str: The input provided by the user.

    Raises:
        None
    """
    user_input = input(f"{USER_COLOR}{Style.BRIGHT}You:{Style.RESET_ALL} ")
    return user_input
