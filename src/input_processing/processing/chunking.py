import json
import re
import uuid
from typing import List, Dict, Any
from collections import defaultdict
import tiktoken
import asyncio
from tqdm import tqdm
import logging
import os
from datetime import datetime, timedelta


from src.utils.config import BASE_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, LOG_DIR, GOOGLE_API_KEY
from src.utils.logger import setup_logger

logger = setup_logger(__name__, 'chunking.log', level=logging.DEBUG)

MAX_TOKENS = 1000

class InputProcessor:
    """Handles loading and validating the input JSON data."""

    def __init__(self, file_name: str):
        """Initialize the InputProcessor with the input file name."""
        self.file_path = os.path.join(RAW_DATA_DIR, file_name)

    def load_json(self) -> Dict[str, Any]:
        """Load JSON data from the file."""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in input file: {e}")
        except IOError as e:
            raise IOError(f"Error reading input file: {e}")

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate the structure of the input data."""
        if not isinstance(data, dict):
            return False
        if 'base_url' not in data or not isinstance(data['base_url'], str):
            return False
        if 'timestamp' not in data or not isinstance(data['timestamp'], str):
            return False
        if 'data' not in data or not isinstance(data['data'], list):
            return False
        for page in data['data']:
            if not isinstance(page, dict):
                return False
            if 'markdown' not in page or not isinstance(page['markdown'], str):
                return False
            if 'metadata' not in page or not isinstance(page['metadata'], dict):
                return False
        return True

class DocumentNode:
    def __init__(self, level, content):
        self.level = level
        self.content = content
        self.children = []

class DocumentTree:
    def __init__(self):
        self.root = DocumentNode(0, "Root")
        self.current_node = self.root


class CustomMarkdownParser:
    def __init__(self, max_tokens: int = 1000, soft_limit: int = 800):
        self.max_tokens = max_tokens
        self.soft_limit = soft_limit
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.current_h1 = ""

    def parse_markdown(self, content: str, source_url: str) -> List[Dict[str, Any]]:
        sections = self._split_into_sections(content)
        chunks = []
        for section in sections:
            chunks.extend(self._process_section(section, source_url))
        return chunks

    def _split_into_sections(self, content: str) -> List[str]:
        pattern = r'(^|\n)([^\n]+)\n(=+|-+)\n'
        sections = re.split(pattern, content, flags=re.MULTILINE)
        return [''.join(sections[i:i+4]) for i in range(1, len(sections), 4)]

    def _process_section(self, section: str, source_url: str) -> List[Dict[str, Any]]:
        lines = section.split('\n')
        title = lines[0].strip()
        underline = lines[1].strip()
        content = '\n'.join(lines[2:])

        if '=' in underline:
            self.current_h1 = title
            header_level = 'H1'
        else:
            header_level = 'H2'

        chunks = []
        current_chunk = {
            "source_url": source_url,
            "headers": {"H1": self.current_h1, header_level: title},
            "content": f"{title}\n{underline}\n\n"
        }

        for part in self._split_content(content):
            if self._should_split_chunk(current_chunk, part):
                chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = {
                    "source_url": source_url,
                    "headers": {"H1": self.current_h1, header_level: title},
                    "content": f"{title}\n{underline}\n\n{part}"
                }
            else:
                current_chunk["content"] += part

            # Check for H3 headers
            h3_match = re.match(r'^### (.+)', part.strip())
            if h3_match:
                current_chunk["headers"]["H3"] = h3_match.group(1)

        if current_chunk["content"]:
            chunks.append(self._finalize_chunk(current_chunk))

        return chunks

    def _split_content(self, content: str) -> List[str]:
        patterns = [
            r'(### .*?\n(?:(?!###).*\n)*)',  # H3 sections
            r'(### Parameters.*?)(?=\n#|\Z)',
            r'(```.*?```)',
            r'(\* \* \*.*?)(?=\n#|\Z)'
        ]
        parts = []
        last_end = 0
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                if match.start() > last_end:
                    parts.append(content[last_end:match.start()])
                parts.append(match.group())
                last_end = match.end()
        if last_end < len(content):
            parts.append(content[last_end:])
        return parts

    def _should_split_chunk(self, chunk: Dict[str, Any], new_content: str) -> bool:
        combined_content = chunk["content"] + new_content
        return len(self.tokenizer.encode(combined_content)) > self.soft_limit

    def _finalize_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        chunk["chunk_id"] = str(uuid.uuid4())
        chunk["token_count"] = len(self.tokenizer.encode(chunk["content"]))
        chunk["has_code_block"] = '```' in chunk["content"]
        return chunk

class Chunker:
    def __init__(self, max_tokens: int = 1000, soft_limit: int = 800):
        self.parser = CustomMarkdownParser(max_tokens, soft_limit)

    def parse_markdown(self, markdown_content: str, source_url: str) -> List[Dict[str, Any]]:
        return self.parser.parse_markdown(markdown_content, source_url)


class Summarizer:
    """Handles generating summaries for chunks using Google Gemini 1.5 Flash."""

    def __init__(self, api_key: str):
        """Initialize the Summarizer with the API key for Google Gemini 1.5 Flash."""
        self.api_key = api_key

    async def batch_summarize(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Generate summaries for a batch of chunks."""
        pass

    async def retry_api_call(self, func, max_retries: int = 3, backoff_factor: float = 1.5):
        """Retry an API call with exponential backoff."""
        pass

class Validator:
    def __init__(self, max_tokens: int = 1000, token_threshold: float = 0.02):
        self.max_tokens = max_tokens
        self.token_threshold = token_threshold
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def validate_document(self, original_doc: str, chunks: List[Dict[str, Any]], source_url: str) -> Dict[str, Any]:
        original_tokens = len(self.tokenizer.encode(original_doc))
        chunk_tokens = sum(chunk['token_count'] for chunk in chunks)

        heading_validation = self._validate_headings(original_doc, chunks)
        content_validation = self._validate_content(original_tokens, chunk_tokens)
        size_validation = self._validate_chunk_sizes(chunks)
        url_validation = self._validate_urls(chunks, source_url)

        return {
            "heading_preservation": heading_validation,
            "content_preservation": content_validation,
            "chunk_size_validation": size_validation,
            "url_consistency": url_validation
        }

    def _validate_headings(self, original_doc: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        original_h1 = len(re.findall(r'\n[^\n]+\n=+\n', original_doc))
        original_h2 = len(re.findall(r'\n[^\n]+\n-+\n', original_doc))
        original_h3 = len(re.findall(r'\n### ', original_doc))
        chunk_h1 = len(set(chunk['headers']['H1'] for chunk in chunks if 'H1' in chunk['headers']))
        chunk_h2 = len(set(chunk['headers']['H2'] for chunk in chunks if 'H2' in chunk['headers']))
        chunk_h3 = len(set(chunk['headers']['H3'] for chunk in chunks if 'H3' in chunk['headers']))

        return {
            "original_h1_count": original_h1,
            "chunk_h1_count": chunk_h1,
            "original_h2_count": original_h2,
            "chunk_h2_count": chunk_h2,
            "original_h3_count": original_h3,
            "chunk_h3_count": chunk_h3,
            "all_headings_preserved": original_h1 == chunk_h1 and original_h2 == chunk_h2 and original_h3 == chunk_h3
        }

    def _validate_content(self, original_tokens: int, chunk_tokens: int) -> Dict[str, Any]:
        difference = abs(original_tokens - chunk_tokens)
        difference_percentage = difference / original_tokens

        return {
            "original_token_count": original_tokens,
            "chunk_total_token_count": chunk_tokens,
            "token_difference_percentage": round(difference_percentage * 100, 2),
            "within_threshold": difference_percentage <= self.token_threshold
        }

    def _validate_chunk_sizes(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        oversized_chunks = [chunk for chunk in chunks if chunk['token_count'] > self.max_tokens]

        return {
            "chunks_within_limit": len(chunks) - len(oversized_chunks),
            "oversized_chunks": len(oversized_chunks),
            "max_chunk_size": max(chunk['token_count'] for chunk in chunks)
        }

    def _validate_urls(self, chunks: List[Dict[str, Any]], source_url: str) -> Dict[str, bool]:
        return {
            "consistent_urls": all(chunk['source_url'] == source_url for chunk in chunks)
        }

class StatisticsGenerator:
    def __init__(self):
        self.document_sizes = []
        self.chunk_sizes = []
        self.chunks_with_code_blocks = 0
        self.heading_counts = {"H1": 0, "H2": 0, "H3": 0}
        self.chunks_per_h2 = []

    def process_document(self, doc: str, chunks: List[Dict[str, Any]]):
        self.document_sizes.append(sum(chunk['token_count'] for chunk in chunks))

        current_h2_chunks = 0
        current_h2 = None
        for chunk in chunks:
            self.chunk_sizes.append(chunk['token_count'])
            if chunk['has_code_block']:
                self.chunks_with_code_blocks += 1

            for header_type in ['H1', 'H2', 'H3']:
                if header_type in chunk['headers']:
                    self.heading_counts[header_type] += 1

            if chunk['headers'].get('H2') != current_h2:
                if current_h2_chunks > 0:
                    self.chunks_per_h2.append(current_h2_chunks)
                current_h2_chunks = 1
                current_h2 = chunk['headers'].get('H2')
            else:
                current_h2_chunks += 1

        if current_h2_chunks > 0:
            self.chunks_per_h2.append(current_h2_chunks)

    def generate_statistics(self) -> Dict[str, Any]:
        return {
            "document_stats": self._get_document_stats(),
            "chunk_stats": self._get_chunk_stats(),
            "heading_stats": self._get_heading_stats()
        }

    def _get_document_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self.document_sizes),
            "avg_document_size": round(sum(self.document_sizes) / len(self.document_sizes)),
            "largest_document": max(self.document_sizes),
            "smallest_document": min(self.document_sizes)
        }

    def _get_chunk_stats(self) -> Dict[str, Any]:
        distribution = defaultdict(int)
        for size in self.chunk_sizes:
            bucket = (size - 1) // 250 * 250
            distribution[f"{bucket}-{bucket + 250}"] += 1

        return {
            "total_chunks": len(self.chunk_sizes),
            "avg_chunk_size": round(sum(self.chunk_sizes) / len(self.chunk_sizes), 2),
            "chunk_size_distribution": dict(sorted(distribution.items())),
            "chunks_with_code_blocks": self.chunks_with_code_blocks
        }

    def _get_heading_stats(self) -> Dict[str, Any]:
        return {
            "total_h1": self.heading_counts['H1'],
            "total_h2": self.heading_counts['H2'],
            "total_h3": self.heading_counts['H3'],
            "avg_chunks_per_h2": round(
                sum(self.chunks_per_h2) / len(self.chunks_per_h2)) if self.chunks_per_h2 else 0
        }

class Orchestrator:
    def __init__(self, input_file: str, output_file: str, max_tokens: int = 1000, soft_limit: int = 800):
        self.input_file = input_file
        self.output_file = output_file
        self.max_tokens = max_tokens
        self.soft_limit = soft_limit
        self.input_processor = InputProcessor(input_file)
        self.chunker = Chunker(max_tokens, soft_limit)
        self.validator = Validator(max_tokens)
        self.stats_generator = StatisticsGenerator()

    async def run(self):
        input_data = self.input_processor.load_json()
        if not self.input_processor.validate_input(input_data):
            raise ValueError("Invalid input data structure")

        all_chunks = []
        validation_reports = []

        for doc in tqdm(input_data['data'], desc="Processing documents"):
            chunks = self.chunker.parse_markdown(doc['markdown'], doc['metadata']['sourceURL'])
            all_chunks.extend(chunks)

            validation_report = self.validator.validate_document(
                doc['markdown'], chunks, doc['metadata']['sourceURL']
            )
            validation_reports.append(validation_report)

            self.stats_generator.process_document(doc['markdown'], chunks)

        statistics = self.stats_generator.generate_statistics()
        validation_report = self._aggregate_validation_reports(validation_reports)

        self.print_results(statistics, validation_report)

        output = {
            "metadata": {
                "input_file": self.input_file,
                "timestamp": datetime.now().isoformat(),
                "total_documents": len(input_data['data']),
                "total_chunks": len(all_chunks)
            },
            "chunks": all_chunks,
            "validation_report": validation_report,
            "statistics": statistics
        }

        with open(self.output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Processing complete. Output saved to {self.output_file}")

    def _aggregate_validation_reports(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        aggregated = {
            "heading_preservation": {
                "original_h1_count": sum(
                    r["heading_preservation"]["original_h1_count"] for r in reports),
                "chunk_h1_count": sum(r["heading_preservation"]["chunk_h1_count"] for r in reports),
                "original_h2_count": sum(
                    r["heading_preservation"]["original_h2_count"] for r in reports),
                "chunk_h2_count": sum(r["heading_preservation"]["chunk_h2_count"] for r in reports),
                "all_headings_preserved": all(
                    r["heading_preservation"]["all_headings_preserved"] for r in reports)
            },
            "content_preservation": {
                "original_token_count": sum(
                    r["content_preservation"]["original_token_count"] for r in reports),
                "chunk_total_token_count": sum(
                    r["content_preservation"]["chunk_total_token_count"] for r in reports),
                "token_difference_percentage": sum(
                    r["content_preservation"]["token_difference_percentage"] for r in
                    reports) / len(reports),
                "within_threshold": all(
                    r["content_preservation"]["within_threshold"] for r in reports)
            },
            "chunk_size_validation": {
                "chunks_within_limit": sum(
                    r["chunk_size_validation"]["chunks_within_limit"] for r in reports),
                "oversized_chunks": sum(
                    r["chunk_size_validation"]["oversized_chunks"] for r in reports),
                "max_chunk_size": max(r["chunk_size_validation"]["max_chunk_size"] for r in reports)
            },
            "url_consistency": {
                "consistent_urls": all(r["url_consistency"]["consistent_urls"] for r in reports)
            }
        }
        return aggregated

    def print_results(self, statistics, validation_report):
        print("\n--- Statistics ---")
        print(f"Total documents: {statistics['document_stats']['total_documents']}")
        print(f"Average document size: {statistics['document_stats']['avg_document_size']} tokens")
        print(f"Total chunks: {statistics['chunk_stats']['total_chunks']}")
        print(f"Average chunk size: {statistics['chunk_stats']['avg_chunk_size']} tokens")
        print(f"Chunks with code blocks: {statistics['chunk_stats']['chunks_with_code_blocks']}")
        print(f"Total H1 headings: {statistics['heading_stats']['total_h1']}")
        print(f"Total H2 headings: {statistics['heading_stats']['total_h2']}")
        print(f"Total H3 headings: {statistics['heading_stats']['total_h3']}")

        print("\n--- Validation Report ---")
        print(
            f"All headings preserved: {validation_report['heading_preservation']['all_headings_preserved']}")
        print(
            f"Content within threshold: {validation_report['content_preservation']['within_threshold']}")
        print(f"Oversized chunks: {validation_report['chunk_size_validation']['oversized_chunks']}")
        print(f"URLs consistent: {validation_report['url_consistency']['consistent_urls']}")


if __name__ == "__main__":
    try:
        input_file = "supabase.com_docs__20240826_212435.json"
        output_file = os.path.join(PROCESSED_DATA_DIR,
                                   f"processed_supabase_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        orchestrator = Orchestrator(input_file, output_file, MAX_TOKENS)
        asyncio.run(orchestrator.run())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise