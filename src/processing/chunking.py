from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core import Document

import os
import json

from src.utils.config import NEW_RAW_DATA_DIR

parser = MarkdownNodeParser()

input_filepath=os.path.join(NEW_RAW_DATA_DIR, 'cra_supabase_docs_2024-09-08 22:21:45.json')

with open(input_filepath, 'r', encoding='utf-8') as f:
    doc = json.load(f)

markdown_docs = []
for item in doc['data']:
    markdown = Document(text=item['markdown'])
    markdown_docs.append(markdown)
# markdown_doc = doc['data'][0]['markdown']
# print(markdown_doc)
nodes = parser.get_nodes_from_documents(markdown_docs)
for index, node in enumerate(nodes):
    print(f"Node {index + 1}:")
    print(node)

import re
from typing import List, Dict, Any, Optional, Sequence
from llama_index.node_parser.node_parser import NodeParser
from llama_index import BaseNode, TextNode
from llama_index.callbacks import CallbackManager
from llama_index.utils import get_tqdm_iterable
from llama_index.node_parser.utils import build_nodes_from_splits
import tiktoken


class ImprovedMarkdownNodeParser(NodeParser):
    """Improved Markdown node parser.
    Splits a document into Nodes using custom Markdown splitting logic.
    """

    def __init__(
            self,
            include_metadata: bool = True,
            include_prev_next_rel: bool = True,
            callback_manager: Optional[CallbackManager] = None,
            hard_limit: int = 1000,
            soft_limit: int = 800,
            overlap_ratio: float = 0.05,
    ):
        super().__init__(callback_manager)
        self.include_metadata = include_metadata
        self.include_prev_next_rel = include_prev_next_rel
        self.hard_limit = hard_limit
        self.soft_limit = soft_limit
        self.overlap_ratio = overlap_ratio
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.previous_chunk_end = ""

    @classmethod
    def from_defaults(
            cls,
            include_metadata: bool = True,
            include_prev_next_rel: bool = True,
            callback_manager: Optional[CallbackManager] = None,
            hard_limit: int = 1000,
            soft_limit: int = 800,
            overlap_ratio: float = 0.05,
    ) -> "ImprovedMarkdownNodeParser":
        return cls(
            include_metadata=include_metadata,
            include_prev_next_rel=include_prev_next_rel,
            callback_manager=callback_manager,
            hard_limit=hard_limit,
            soft_limit=soft_limit,
            overlap_ratio=overlap_ratio,
        )

    def parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        all_nodes: List[BaseNode] = []
        nodes_with_progress = get_tqdm_iterable(nodes, show_progress, "Parsing nodes")
        for node in nodes_with_progress:
            nodes = self.get_nodes_from_node(node)
            all_nodes.extend(nodes)
        return all_nodes

    def get_nodes_from_node(self, node: BaseNode) -> List[TextNode]:
        text = node.get_content(metadata_mode=MetadataMode.NONE)
        markdown_nodes = []
        lines = text.split("\n")
        metadata: Dict[str, str] = {}
        current_section = ""
        current_tokens = 0
        code_block = False

        for line in lines:
            if line.lstrip().startswith("```"):
                code_block = not code_block

            header_match = re.match(r"^(#+)\s(.*)", line)
            if header_match and not code_block:
                if current_section and current_tokens >= self.soft_limit:
                    markdown_nodes.append(self._build_node_from_split(current_section.strip(), node, metadata))
                    current_section = ""
                    current_tokens = 0

                metadata = self._update_metadata(metadata, header_match.group(2), len(header_match.group(1).strip()))
                current_section += f"{line}\n"
                current_tokens += self._count_tokens(line)
            else:
                new_tokens = self._count_tokens(line)
                if current_tokens + new_tokens > self.hard_limit and not code_block:
                    markdown_nodes.append(self._build_node_from_split(current_section.strip(), node, metadata))
                    current_section = ""
                    current_tokens = 0

                current_section += f"{line}\n"
                current_tokens += new_tokens

        if current_section:
            markdown_nodes.append(self._build_node_from_split(current_section.strip(), node, metadata))

        return markdown_nodes

    def _update_metadata(
            self, headers_metadata: dict, new_header: str, new_header_level: int
    ) -> dict:
        updated_headers = {}
        for i in range(1, new_header_level):
            key = f"Header_{i}"
            if key in headers_metadata:
                updated_headers[key] = headers_metadata[key]
        updated_headers[f"Header_{new_header_level}"] = new_header
        return updated_headers

    def _build_node_from_split(
            self,
            text_split: str,
            node: BaseNode,
            metadata: dict,
    ) -> TextNode:
        overlap_tokens = int(self.soft_limit * self.overlap_ratio)
        overlap_text = self.previous_chunk_end

        full_text = overlap_text + text_split
        self.previous_chunk_end = text_split[-overlap_tokens:]

        new_node = build_nodes_from_splits([full_text], node, id_func=self.id_func)[0]
        if self.include_metadata:
            new_node.metadata = {**new_node.metadata, **metadata}

        return new_node

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))