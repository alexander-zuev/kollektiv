import json
import os
from tqdm import tqdm
import tiktoken

def test_chunker(input_file: str, max_tokens: int = 1000):
    from src.input_processing.processing.chunking import InputProcessor, Chunker

    processor = InputProcessor(input_file)
    chunker = Chunker(max_tokens=max_tokens)
    tokenizer = tiktoken.get_encoding("cl100k_base")

    try:
        loaded_data = processor.load_json()
        if not processor.validate_input(loaded_data):
            raise ValueError("Input data structure is invalid")

        all_chunks = []
        total_pages = len(loaded_data['data'])
        total_chunks = 0
        total_tokens = 0
        total_original_tokens = 0
        headers_count = {"H1": 0, "H2": 0}
        original_headers_count = {"H1": 0, "H2": 0}

        for i, page in enumerate(tqdm(loaded_data['data'], desc="Processing pages")):
            markdown_content = page['markdown']
            source_url = page['metadata']['sourceURL']

            # Count original tokens
            total_original_tokens += len(tokenizer.encode(markdown_content))

            # Count original headers using the same method as CustomMarkdownParser
            lines = markdown_content.split('\n')
            for i in range(len(lines) - 1):
                if set(lines[i + 1]) == {'='}:
                    original_headers_count["H1"] += 1
                elif set(lines[i + 1]) == {'-'}:
                    original_headers_count["H2"] += 1

            chunks = chunker.parse_markdown(markdown_content, source_url)
            all_chunks.extend(chunks)
            total_chunks += len(chunks)
            total_tokens += sum(chunk['token_count'] for chunk in chunks)

            # Count headers in chunks
            for chunk in chunks:
                if chunk['headers']['H1']:
                    headers_count["H1"] += 1
                if chunk['headers']['H2']:
                    headers_count["H2"] += 1

        # Log full chunk content to a file
        log_file = 'chunking_log.txt'
        with open(log_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(f"Chunk ID: {chunk['chunk_id']}\n")
                f.write(f"Source URL: {chunk['source_url']}\n")
                f.write(f"Headers: {json.dumps(chunk['headers'], indent=2)}\n")
                f.write(f"Token Count: {chunk['token_count']}\n")
                f.write(f"Has Code Block: {chunk['has_code_block']}\n")
                f.write(f"Content:\n{chunk['content']}\n\n")
                f.write("-" * 80 + "\n\n")

        # Print summary statistics
        print(f"\nAnalytical Validation Results:")
        print(f"Total Pages Processed: {total_pages}")
        print(f"Total Chunks Created: {total_chunks}")
        print(f"Total Tokens in Chunks: {total_tokens}")
        print(f"Total Original Tokens: {total_original_tokens}")
        print(f"Token Coverage: {total_tokens / total_original_tokens:.2%}")
        print(f"Average Tokens per Chunk: {total_tokens / total_chunks:.2f}")
        print(f"\nHeader Capture:")
        print(f"Original H1 Headers: {original_headers_count['H1']}")
        print(f"Captured H1 Headers: {headers_count['H1']}")
        print(f"Original H2 Headers: {original_headers_count['H2']}")
        print(f"Captured H2 Headers: {headers_count['H2']}")
        print(f"\nHeader Capture Rate:")
        print(f"H1 Capture Rate: {headers_count['H1'] / max(original_headers_count['H1'], 1):.2%}")
        print(f"H2 Capture Rate: {headers_count['H2'] / max(original_headers_count['H2'], 1):.2%}")
        print(f"\nFull chunk content logged to: {log_file}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    input_file = "supabase.com_docs__20240826_212435.json"  # Replace with the actual path
    max_tokens = 1000  # Adjust as needed
    test_chunker(input_file, max_tokens)