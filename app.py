from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import ANTHROPIC_API_KEY

def main():
    assistant = ClaudeAssistant(api_key=ANTHROPIC_API_KEY)
    assistant.init()

    # Load documents (if needed)
    # assistant.load_documents(documents)

    while True:
        query = input("Enter your question (or 'quit' to exit): ")
        if query.lower() == 'quit':
            break
        response = assistant.process_query(query)
        print(f"Claude: {response}")

if __name__ == "__main__":
    main()