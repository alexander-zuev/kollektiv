from src.input_processing.processing.chunking import InputProcessor, MarkdownParser
import os

def test_markdown_parser():
    input_file = "supabase.com_docs__20240826_212435.json"  # Replace with your actual file name
    input_processor = InputProcessor(input_file)
    markdown_parser = MarkdownParser()

    input_data = input_processor.load_json()
    if not input_processor.validate_input(input_data):
        raise ValueError("Input data is invalid.")

    for page in input_data['data']:
        markdown_content = page['markdown']
        source_url = page['metadata']['sourceURL']
        parsed_elements = markdown_parser.parse(markdown_content)

        print(f"Source URL: {source_url}")
        for i, element in enumerate(parsed_elements):
            print(f"  Element {i + 1}:")
            print(f"    Type: {element['type']}")
            if element['type'] == 'heading':
                print(f"    Level: {element['level']}")
            print(f"    Content: {element['content']}")

if __name__ == "__main__":
    test_markdown_parser()