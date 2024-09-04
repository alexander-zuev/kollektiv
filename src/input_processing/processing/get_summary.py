import json
import tiktoken
import os
from tqdm import tqdm

from src.utils.config import BASE_DIR


def process_large_json(filename, max_pages=None):
    url_count = 0
    total_tokens = 0
    content_lengths = []
    enc = tiktoken.get_encoding("cl100k_base")

    filepath = os.path.join(BASE_DIR, "src", "input_processing", "data", "raw", filename)

    file_size = os.path.getsize(filepath)

    with open(filepath, 'r') as f:
        data = json.load(f)
        pages = data.get('data', [])

        if max_pages:
            pages = pages[:max_pages]

        for page in tqdm(pages, desc="Processing pages", unit="page"):
            url_count += 1
            content = page.get('content', '')
            markdown = page.get('markdown', '')

            # Count tokens in content and markdown
            content_tokens = len(enc.encode(content))
            markdown_tokens = len(enc.encode(markdown))
            total_tokens += content_tokens + markdown_tokens

            content_lengths.append(len(content))

    # Calculate summary statistics
    avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
    max_content_length = max(content_lengths) if content_lengths else 0
    min_content_length = min(content_lengths) if content_lengths else 0

    # Print summary
    print(f"\nFile: {filename}")
    print(f"File size: {file_size / (1024 * 1024):.2f} MB")
    print(f"Number of URLs processed: {url_count}")
    print(f"Total tokens: {total_tokens}")
    print(f"Average content length: {avg_content_length:.2f} characters")
    print(f"Max content length: {max_content_length} characters")
    print(f"Min content length: {min_content_length} characters")


if __name__ == "__main__":
    filename = "supabase.com_docs__20240830_073045.json"  # Change this to your filename
    max_pages = 1000  # Adjust this value to process more or fewer pages
    process_large_json(filename, max_pages)