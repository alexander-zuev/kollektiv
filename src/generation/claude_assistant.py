from src.utils.logger import setup_logger
from src.utils.config import ANTHROPIC_API_KEY

import anthropic
import os

# Client Class
class Claude:
    def __init__(self, api_key :str =ANTHROPIC_API_KEY, model_name:str ="sonnet-3.5-1024"):
        self.client = None
        self.api_key = api_key
        self.model_name = model_name
        self.logger = setup_logger(__name__, "claude_assistant.log")

    def get_response(self, user_query: str, streaming: bool = False):
        pass