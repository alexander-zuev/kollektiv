from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


def print_assistant_message(message: str, end: str = "\n", flush: bool = True):
    print(f"{Fore.BLUE}{message}{Style.RESET_ALL}", end=end, flush=flush)
