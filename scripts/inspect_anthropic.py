"""Script to inspect Anthropic package types."""

from anthropic import __version__
from anthropic.types import (
    MessageStartEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
)


def main():
    """Print Anthropic package version and available event types."""
    print(f"Anthropic version: {__version__}")
    print("\nAvailable event types:")

    event_types = [
        MessageStartEvent,
        MessageDeltaEvent,
        MessageStopEvent,
        ContentBlockStartEvent,
        ContentBlockStopEvent,
    ]

    for event_type in event_types:
        print(f"\n- {event_type.__name__}")
        if hasattr(event_type, "__annotations__"):
            print("  Attributes:")
            for attr, type_hint in event_type.__annotations__.items():
                print(f"    - {attr}: {type_hint}")


if __name__ == "__main__":
    main()
