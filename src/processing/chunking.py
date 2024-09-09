from pprint import pprint


from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,)

import os
import json

from src.utils.config import NEW_RAW_DATA_DIR


input_filepath=os.path.join(NEW_RAW_DATA_DIR, 'cra_supabase_docs_2024-09-08 22:21:45.json')

with open(input_filepath, 'r', encoding='utf-8') as f:
    doc = json.load(f)

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
]

markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,
                                               strip_headers=False)

# Let's split further
chunk_size = 1000
chunk_overlap = chunk_size * 0.1 # 5%
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size, chunk_overlap=chunk_overlap
)

results = []
for item in doc['data']:
    markdown = item['markdown']
    md_header_splits = markdown_splitter.split_text(markdown)
    text_splits = text_splitter.split_documents(md_header_splits)
    results.extend(text_splits)

for result in results:
    print("New chunk")
    print(f"Metadata: {result.metadata}")
    print(f"Text: {result.page_content}")
    print(f"\n\n--------------------\n\n")