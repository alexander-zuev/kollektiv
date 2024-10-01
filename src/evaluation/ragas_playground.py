import json
import os.path
from collections.abc import Sequence
from pprint import pprint

from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from ragas import evaluate
from ragas.evaluation import Result
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
from ragas.testset.evolutions import multi_context, reasoning, simple
from ragas.testset.generator import DataRow, TestDataset, TestsetGenerator

from src.utils.config import EVAL_DIR, RAW_DATA_DIR
from utils.decorators import base_error_handler
from utils.logger import configure_logging, get_logger

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

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], **kwargs) -> TestDataset:
        eval_dataset = self.generator.generate_with_langchain_docs(
            documents=documents, **kwargs, distributions={simple: 0.25, reasoning: 0.25, multi_context: 0.5}
        )
        return eval_dataset

    @base_error_handler
    def save_to_json(self, eval_dataset: TestDataset, filename: str = "eval_dataset.json") -> str:

        filepath = os.path.join(self.dataset_path, filename)

        data = {
            "test_data": [
                {
                    "question": row.question,
                    "contexts": row.contexts,
                    "ground_truth": row.ground_truth,
                    "evolution_type": row.evolution_type,
                    "metadata": row.metadata,
                }
                for row in eval_dataset.test_data
            ]
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error(f"Error saving dataset to JSON: {str(e)}")
            raise

        logger.info(f"Dataset saved to JSON: {filepath}")
        return filepath

    def load_from_json(self, filename: str = "eval_dataset.json") -> TestDataset | None:
        filepath = os.path.join(self.dataset_path, filename)

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Please ensure the file exists: {filepath}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding json {e}")

        # Reconstruct TestDataset object
        try:
            logger.info("Reconstructing the TestDataset object...")
            test_data = [DataRow(**row_data) for row_data in data["test_data"]]
            dataset = TestDataset(test_data=test_data)
            logger.info(f"Loaded dataset with {len(dataset.test_data)} test cases")
            return dataset
        except Exception as e:
            logger.error(f"Error reconstructing dataset: {str(e)}")
            return None


# TODO: Add responses to the dataset based on my retriever so that we can test it


class Evaluator:
    def __init__(
        self,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.llm = OpenAI(model=model)
        self.embeddings = OpenAIEmbedding(model=embedding_model)

    def evaluate(self, dataset) -> Result:
        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ],
                llm=OpenAI(model="gpt-4o"),
                embeddings=OpenAIEmbedding(model="text-embedding-3-small"),
            )
            return result
        except Exception as e:
            logger.error(f"An error happend {e}")
            raise


def main():
    configure_logging()

    load_dotenv()

    filename = "docs_anthropic_com_en_20240928_135426.json"

    documents = DataLoader(filename=filename).get_documents()
    generator = DatasetGenerator()
    eval_dataset = generator.generate_dataset(documents=documents, test_size=5)
    generator.save_to_json(eval_dataset)

    eval_dataset = generator.load_from_json()
    pprint(eval_dataset)

    eval_dataset = eval_dataset.to_dataset()

    pprint(eval_dataset)

    eval_result = Evaluator().evaluate(eval_dataset)
    pprint(eval_result)


if __name__ == "__main__":
    main()
