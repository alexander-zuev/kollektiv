# test_input_processor.py

import os
from src.utils.config import RAW_DATA_DIR
from src.input_processing.processing.chunking import InputProcessor

def test_input_processor():
    file_name = "supabase.com_docs__20240826_212435.json"
    processor = InputProcessor(file_name)

    try:
        # Test load_json
        loaded_data = processor.load_json()
        print(f"Successfully loaded JSON data from {file_name}")

        # Test validate_input
        if processor.validate_input(loaded_data):
            print("Input data structure is valid")
        else:
            print("Input data structure is invalid")

        # Print some basic information about the loaded data
        print(f"Base URL: {loaded_data['base_url']}")
        print(f"Timestamp: {loaded_data['timestamp']}")
        print(f"Number of pages: {len(loaded_data['data'])}")

        # Print information about the first page
        first_page = loaded_data['data'][0]
        print("\nFirst page information:")
        print(f"Markdown length: {len(first_page['markdown'])}")
        print(f"Metadata keys: {', '.join(first_page['metadata'].keys())}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    test_input_processor()