import os
import json
from urllib.parse import urlparse

# Define the correct paths relative to the script location
filename = 'supabase.com_docs__20240826_212435.json'
current_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(current_dir, '..', 'data', 'raw', filename)
OUTPUT_DIR = os.path.join(current_dir, '..', 'data', 'formatted')

def get_absolute_path(path):
    return os.path.abspath(path)

def analyze_content_structure(data, output_dir=OUTPUT_DIR):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Number of URLs parsed
    num_urls = len(data)

    # Dictionary to hold URLs grouped by root domain
    urls_by_root = {}

    # Sample files
    sample_markdown = []
    sample_content = []

    for item in data[:3]:  # Limiting to first 3 items for samples
        sample_markdown.append(f"# {item['metadata']['sourceURL']}\n{item['markdown']}")
        sample_content.append(f"# {item['metadata']['sourceURL']}\n{item['content']}")

        # Parse URL to get the root domain
        parsed_url = urlparse(item['metadata']['sourceURL'])
        root_domain = parsed_url.netloc

        # Group URLs by root domain
        if root_domain not in urls_by_root:
            urls_by_root[root_domain] = []
        urls_by_root[root_domain].append(item['metadata']['sourceURL'])

    # Writing summary stats including URLs by root domain
    with open(os.path.join(output_dir, 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write(f"Number of URLs parsed: {num_urls}\n\n")
        f.write("URLs by root domain:\n")
        for root, urls in urls_by_root.items():
            f.write(f"\n{root}:\n")
            for url in urls:
                f.write(f"  - {url}\n")

    # Writing sample markdown file
    with open(os.path.join(output_dir, 'sample_markdown.md'), 'w', encoding='utf-8') as f:
        f.write("\n\n".join(sample_markdown))

    # Writing sample content file
    with open(os.path.join(output_dir, 'sample_content.md'), 'w', encoding='utf-8') as f:
        f.write("\n\n".join(sample_content))

    print(f"Summary and samples written to: {get_absolute_path(output_dir)}")

# Print current working directory for debugging
print(f"Current working directory: {os.getcwd()}")

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the data file relative to the script's location
data_file_path = os.path.join(current_dir, '..', 'data', 'raw', filename)

# Print the path we're trying to open for debugging
print(f"Attempting to open file at: {get_absolute_path(data_file_path)}")

# Check if the file exists before trying to open it
if not os.path.exists(data_file_path):
    print(f"File does not exist at: {data_file_path}")
    exit(1)

# Load your data from the file
with open(data_file_path, 'r') as f:
    json_data = json.load(f)
    data = json_data['data']  # 'data' is a top-level key in your JSON

# Analyze content structure
analyze_content_structure(data)

# Print summary stats
print(f"Number of URLs parsed: {len(data)}")