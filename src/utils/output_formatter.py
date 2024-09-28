from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

ASSISTANT_COLOR = Fore.LIGHTBLUE_EX
USER_COLOR = Fore.GREEN


def print_assistant_stream(message: str, end: str = "\n", flush: bool = True):
    print(f"{ASSISTANT_COLOR}{message}{Style.RESET_ALL}", end=end, flush=flush)


def print_welcome_message(message: str):
    print(f"\n{ASSISTANT_COLOR}{message}{Style.RESET_ALL}")


def user_input():
    user_input = input(f"{USER_COLOR}{Style.BRIGHT}You:{Style.RESET_ALL} ")
    return user_input
