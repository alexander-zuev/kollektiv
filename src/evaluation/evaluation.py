import json
import os.path
from collections.abc import Sequence
from datetime import datetime

import weave
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
from weave import Dataset as WeaveDataset
from weave.trace import weave_client

from generation.claude_assistant import ClaudeAssistant
from src.utils.config import EVAL_DIR, RAW_DATA_DIR, WEAVE_PROJECT_NAME
from utils.decorators import anthropic_error_handler, base_error_handler
from utils.logger import configure_logging, get_logger
from vector_storage.vector_db import Reranker, ResultRetriever, VectorDB

logger = get_logger()


class DataLoader:
    def __init__(self):
        self.dataset_path = EVAL_DIR
        self.dataset_filename: str = "eval_dataset.json"

    @base_error_handler
    def get_documents(self, filename: str):
        filepath = os.path.join(RAW_DATA_DIR, filename)
        loader = JSONLoader(
            file_path=filepath,
            jq_schema=".data[]",
            content_key="markdown",
            metadata_func=self.metadata_func,
        )

        documents = loader.load()
        logger.info(f"Successfully loaded documents from {filename}")
        return documents

    def metadata_func(self, record: dict, metadata: dict) -> dict:
        metadata["title"] = record.get("metadata", {}).get("title", "")
        metadata["url"] = record.get("metadata", {}).get("sourceURL", "")
        metadata["description"] = record.get("metadata", {}).get("description", "")

        return metadata

    @base_error_handler
    def save_dataset(self, dataset: Dataset, filename: str = None) -> str:
        """Saves the given object to json file"""
        if filename != self.dataset_filename:
            self.dataset_filename = filename
            logger.debug(f"Updated filename to: {self.dataset_filename}")

        filepath = os.path.join(self.dataset_path, filename)
        try:
            data_dict = dataset.to_dict()
            with open(filepath, "w") as f:
                json.dump(data_dict, f, indent=2)
            logger.info(f"Dataset saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving dataset to JSON: {str(e)}")
            raise

    @base_error_handler
    def load_json(self, filename: str = None) -> Dataset | None:
        """Loads the dataset from json file"""
        if filename:
            self.dataset_filename = filename

        filepath = os.path.join(self.dataset_path, self.dataset_filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
                num_samples = len(data["question"])  # or any other key that represents the number of samples

                dataset = Dataset.from_dict(data)
            logger.info(f"Loaded dataset with {num_samples} samples")
            return dataset
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON file {filepath}, invalid format")
            raise
        except Exception as e:
            logger.error(f"Error loading dataset from JSON: {str(e)}")
            raise


class DatasetGenerator:
    def __init__(
        self,
        generator_llm: str = "gpt-4o",
        critic_llm: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        dataset_path: str = EVAL_DIR,
        claude_assistant: ClaudeAssistant = None,
        loader: DataLoader = None,
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
        self.dataset_filename: str = "eval_dataset.json"
        self.loader = loader or DataLoader()
        self.weave_dataset_name: str = None

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], **kwargs) -> TestDataset:
        eval_dataset = self.generator.generate_with_langchain_docs(
            documents=documents, **kwargs, distributions={simple: 0.25, reasoning: 0.25, multi_context: 0.5}
        )
        self.dataset = eval_dataset
        return eval_dataset

    @anthropic_error_handler
    def get_rag_answers(self) -> Dataset:
        """Takes synthetic dataset from Ragas, generates and answer and converts to HF Dataset"""
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
        self.loader.save_dataset(dataset, self.dataset_filename)
        logger.info(f"Saved the dataset {self.dataset_filename}.json to {self.dataset_path}")
        return self.dataset


class WeaveManager:
    def __init__(
        self,
        project_name: str = WEAVE_PROJECT_NAME,
    ):
        self.project_name = project_name
        weave.init(project_name)

    def upload_dataset(self, dataset: Dataset, name: str) -> str:
        """Uploads dataset to Weave"""
        # Convert HuggingFace Dataset to a list of dictionaries
        data_list = dataset.to_list()

        # Create a Weave Dataset
        weave_dataset = WeaveDataset(name=name, rows=data_list)

        try:
            # Publish the dataset
            weave.publish(weave_dataset)

            logger.info(f"Dataset '{name!r}' uploaded to Weave")
            return name
        except Exception as e:
            logger.error(f"An error occurred while uploading dataset to Weave: {str(e)}")
            raise

    def retrieve_dataset(self, name: str) -> weave_client.ObjectRef:
        if name is None:
            raise ValueError("Dataset name is required!")
        dataset_name = name

        dataset_ref = weave.ref(dataset_name).get()
        print(dataset_ref)
        return dataset_ref


class Evaluator:
    def __init__(
        self,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.model_name = model
        self.embedding_model_name = embedding_model
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

    def save_results(self, result: Result, dataset: Dataset, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_results_{timestamp}.json"

        filepath = os.path.join(EVAL_DIR, filename)

        results_dict = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "dataset_size": len(dataset),
                "llm_model": self.model_name,
                "embedding_model": self.embedding_model_name,
            },
            "metrics": {},
        }

        for metric_name, metric_value in result.items():
            results_dict["metrics"][metric_name] = float(metric_value)

        with open(filepath, "w") as f:
            json.dump(results_dict, f, indent=2)

        logger.info(f"Evaluation results saved to: {filepath}")
        return filepath

    @staticmethod
    def load_results(filename: str) -> dict | None:
        filepath = os.path.join(EVAL_DIR, filename)
        try:
            with open(filepath) as f:
                results = json.load(f)
            logger.info(f"Loaded evaluation results from: {filepath}")
            return results
        except FileNotFoundError:
            logger.error(f"Results file not found: {filepath}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from file: {filepath}")
            return None


class EvalManager:
    """Orchestrates the pipeline end to end"""

    def __init__(
        self,
        loader: DataLoader = None,
        weave_manager: WeaveManager = None,
        vector_db: VectorDB = None,
        claude_assistant: ClaudeAssistant = None,
        retriever: ResultRetriever = None,
        reranker: Reranker = None,
        generator: DatasetGenerator = None,
        evaluator: Evaluator = None,
    ):
        self.loader = loader or DataLoader()
        self.weave_manager = weave_manager or WeaveManager()
        self.vector_db = vector_db or VectorDB()
        self.claude_assistant = claude_assistant or ClaudeAssistant(vector_db=self.vector_db)
        self.reranker = reranker or Reranker()
        self.retriever = retriever or ResultRetriever(self.vector_db, self.reranker)
        self.claude_assistant.retriever = self.retriever
        self.generator = generator or DatasetGenerator()
        self.evaluator = evaluator or Evaluator()

    def run_evaluation_pipeline(
        self,
        generate_new_dataset: bool = False,
        input_filenames: str = None,
        use_local_dataset: bool = False,
        local_dataset_name: str = "eval_dataset.json",
        weave_dataset_name: str = "anthropic_dataset",
    ):
        """Runs evaluation pipeline with pre-determined parameters"""

        if generate_new_dataset:
            docs = self.loader.get_documents(filename=input_filenames)
            self.generator.generate_dataset(documents=docs, test_size=1)

            dataset = self.generator.get_rag_answers()
        else:
            dataset = self.loader.load_json(filename=local_dataset_name)

        # test uploading
        self.weave_manager.upload_dataset(dataset, name="anthropic_dataset")

        # test retrieval
        dataset_ref = self.weave_manager.retrieve_dataset(name="anthropic_dataset")

        print(dataset_ref.rows[0])


def main():
    configure_logging()

    load_dotenv()

    filename = "docs_anthropic_com_en_20240928_135426.json"

    pipeline_manager = EvalManager()

    # Run the pipeline
    pipeline_manager.run_evaluation_pipeline(generate_new_dataset=False, input_filenames=filename)

    # TODO:
    # Add my own answers
    # Append my context
    # Run evaluation
    # Save the results
    # Download the results


#
#     print("Loading dataset...")
#     eval_dataset = generator.load_dataset()  # using default filename
#
#     pprint(eval_dataset)
#
#     evaluator = Evaluator()
#     eval_result = evaluator.evaluate_metrics(eval_dataset)
#     pprint(eval_result)
#
#     # Save the evaluation results
#     saved_filepath = evaluator.save_results(eval_result, eval_dataset)
#     print(f"Evaluation results saved to: {saved_filepath}")
#
#
if __name__ == "__main__":
    main()
