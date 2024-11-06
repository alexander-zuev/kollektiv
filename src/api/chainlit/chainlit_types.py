from typing import Any, Dict, List, Optional, Union
from chainlit.message import Message, AskUserMessage

# Re-export the types we use
__all__ = ["Message", "AskUserMessage", "StepDict"]


class StepDict(Dict[str, Any]):
    output: str
    id: str
    # ... other fields you use
