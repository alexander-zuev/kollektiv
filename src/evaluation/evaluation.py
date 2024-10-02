import os.path
import pickle
from collections.abc import Sequence
from pprint import pprint

from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from ragas import evaluate
from ragas.evaluation import Result
from ragas.metrics import answer_correctness, answer_relevancy, faithfulness
from ragas.testset.evolutions import multi_context, reasoning, simple
from ragas.testset.generator import TestDataset, TestsetGenerator
from tqdm import tqdm

from generation.claude_assistant import ClaudeAssistant
from src.utils.config import EVAL_DIR, RAW_DATA_DIR
from utils.decorators import anthropic_error_handler, base_error_handler
from utils.logger import configure_logging, get_logger
from vector_storage.vector_db import Reranker, ResultRetriever, VectorDB

logger = get_logger()


class DataLoader:
    def __init__(self, filename: str):
        self.filename = filename

    @base_error_handler
    def get_documents(self):
        filepath = os.path.join(RAW_DATA_DIR, self.filename)
        loader = JSONLoader(
            file_path=filepath,
            jq_schema=".data[]",
            content_key="markdown",
            metadata_func=self.metadata_func,
        )

        documents = loader.load()
        return documents

    def metadata_func(self, record: dict, metadata: dict) -> dict:
        metadata["title"] = record.get("metadata", {}).get("title", "")
        metadata["url"] = record.get("metadata", {}).get("sourceURL", "")
        metadata["description"] = record.get("metadata", {}).get("description", "")

        return metadata


class DatasetGenerator:
    def __init__(
        self,
        generator_llm: str = "gpt-4o",
        critic_llm: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        dataset_path: str = EVAL_DIR,
        claude_assistant: ClaudeAssistant = None,
    ):
        self.generator_llm = OpenAI(model=generator_llm)
        self.critic_llm = OpenAI(model=critic_llm)
        self.embeddings = OpenAIEmbedding(model=embedding_model)
        self.generator = TestsetGenerator.from_llama_index(
            self.generator_llm,
            self.critic_llm,
            self.embeddings,
        )
        self.dataset_path = dataset_path
        self.claude_assistant = claude_assistant
        self.dataset: TestDataset = None
        self.dataset_filename: str = "eval_dataset.pkl"

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], **kwargs) -> TestDataset:
        eval_dataset = self.generator.generate_with_langchain_docs(
            documents=documents, **kwargs, distributions={simple: 0.25, reasoning: 0.25, multi_context: 0.5}
        )
        self.dataset = eval_dataset
        return eval_dataset

    @anthropic_error_handler
    def get_rag_answers(self) -> Dataset:
        """Takes synthethic dataset from Ragas, generates and answer and converts to HF Dataset"""
        if not self.dataset:
            raise ValueError("Dataset not generated, generate the dataset first!")

        data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}

        for _i, row in enumerate(tqdm(self.dataset.test_data, desc="Adding RAG answers")):
            query = row.question
            answer = self.claude_assistant.get_response(query, stream=False)

            data["question"].append(row.question)
            data["answer"].append(answer)
            data["contexts"].append(row.contexts)
            data["ground_truth"].append(row.ground_truth)

        dataset = Dataset.from_dict(data)
        self.dataset = dataset
        # save dataset
        self.save_dataset(self.dataset)
        pprint(self.dataset)
        return self.dataset

    @base_error_handler
    def save_dataset(self, eval_dataset: Dataset, filename: str = "eval_dataset.pkl") -> str:
        if filename != self.dataset_filename:
            self.dataset_filename = filename
            logger.debug(f"Updated filename to: {self.dataset_filename}")

        filepath = os.path.join(self.dataset_path, filename)
        try:
            with open(filepath, "wb") as f:
                pickle.dump(eval_dataset, f)
            logger.info(f"Dataset saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving dataset: {str(e)}")
            raise

    @base_error_handler
    def load_dataset(self, filename: str = "eval_dataset.pkl") -> Dataset | None:
        if filename != self.dataset_filename:
            logger.warning(f"Dataset name differes from self.dataset_name, using user-provided name: {filename}")

        filepath = os.path.join(self.dataset_path, filename)
        try:
            with open(filepath, "rb") as f:
                dataset = pickle.load(f)
            logger.info(f"Loaded dataset with {len(dataset)} samples")
            return dataset
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
        except Exception as e:
            logger.error(f"Error loading dataset: {str(e)}")
        return None


class Evaluator:
    def __init__(
        self,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.llm = OpenAI(model=model)
        self.embeddings = OpenAIEmbedding(model=embedding_model)

    def evaluate_metrics(self, dataset: Dataset) -> Result:
        if dataset is None or len(dataset) == 0:
            raise ValueError("Dataset is empty or not loaded!")

        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    answer_correctness,
                ],
            )
            return result
        except Exception as e:
            logger.error(f"An error happened {e}")
            raise


def main():
    configure_logging()

    load_dotenv()

    filename = "docs_anthropic_com_en_20240928_135426.json"

    # Initialize the retriever
    vector_db = VectorDB()
    claude_assistant = ClaudeAssistant(vector_db=vector_db)
    reranker = Reranker()
    retriever = ResultRetriever(vector_db=vector_db, reranker=reranker)
    claude_assistant.retriever = retriever

    documents = DataLoader(filename=filename).get_documents()
    generator = DatasetGenerator(claude_assistant=claude_assistant)
    generator.generate_dataset(documents=documents, test_size=75)

    print("After adding answers")
    eval_dataset = generator.get_rag_answers()
    pprint(eval_dataset)

    print("Loading dataset...")
    eval_dataset = generator.load_dataset()  # using default filename

    pprint(eval_dataset)

    eval_result = Evaluator().evaluate_metrics(eval_dataset)
    pprint(eval_result)


if __name__ == "__main__":
    main()
