import asyncio
import json
import os.path
from collections.abc import Sequence
from pprint import pprint

import weave
from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from ragas import evaluate
from ragas.cost import get_token_usage_for_openai
from ragas.metrics import answer_correctness, answer_relevancy, context_precision, context_recall, faithfulness
from ragas.testset.evolutions import multi_context, reasoning, simple
from ragas.testset.generator import TestDataset, TestsetGenerator
from weave import Dataset as WeaveDataset
from weave import Model
from weave.trace import weave_client

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import EVAL_DIR, JUDGE_LLM_MODEL, RAW_DATA_DIR, WEAVE_PROJECT_NAME
from src.utils.decorators import anthropic_error_handler, base_error_handler
from src.utils.logger import configure_logging, get_logger
from src.vector_storage.vector_db import Reranker, ResultRetriever, VectorDB
from utils.config import EMBEDDING_MODEL

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
        test_dataset = self.generator.generate_with_langchain_docs(
            documents=documents, **kwargs, distributions={simple: 0.25, reasoning: 0.25, multi_context: 0.5}
        )
        dataset = self.convert_to_dataset(test_dataset)
        self.dataset = dataset
        return dataset

    @anthropic_error_handler
    def convert_to_dataset(self, test_dataset: TestDataset) -> Dataset:
        """Takes synthetic dataset from Ragas and converts to HF Dataset"""
        if not test_dataset:
            raise ValueError("Dataset not generated, generate the dataset first!")

        data = {
            "question": [row.question for row in test_dataset.test_data],
            "contexts": [row.contexts for row in test_dataset.test_data],
            "ground_truth": [row.ground_truth for row in test_dataset.test_data],
        }

        dataset = Dataset.from_dict(data)
        self.dataset = dataset
        return self.dataset


class WeaveManager:
    def __init__(
        self,
        project_name: str = WEAVE_PROJECT_NAME,
    ):
        self.project_name = project_name
        weave.init(project_name)

    async def upload_dataset(self, dataset: Dataset, name: str) -> str:
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

    async def retrieve_dataset(self, name: str) -> weave_client.ObjectRef:
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
        embedding_model: str = EMBEDDING_MODEL,
        claude_assistant: ClaudeAssistant = None,
        judge_llm_model: str = JUDGE_LLM_MODEL,
    ):
        self.model_name = model
        self.embedding_model_name = embedding_model
        self.llm = OpenAI(model=model)
        self.embeddings = OpenAIEmbedding(model=embedding_model)
        self.omni_claude_model = OmniClaudeModel(claude_assistant=claude_assistant)
        self.judge_llm_model = judge_llm_model

    @weave.op()
    async def evaluate_row(self, question: str, ground_truth: str, model_output: dict) -> dict[str, float]:

        answer, contexts = model_output["answer"], model_output["contexts"]

        # prepare data for RAGAS
        data = {
            "question": [question],
            "ground_truth": [ground_truth],
            "answer": [answer],
            "retrieved_contexts": [contexts],
        }

        dataset = Dataset.from_dict(data)

        metrics = [faithfulness, answer_relevancy, answer_correctness, context_recall, context_precision]

        judge_model = ChatOpenAI(model=self.judge_llm_model)
        embeddings_model = OpenAIEmbeddings(model=self.embedding_model_name)

        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=judge_model,
            embeddings=embeddings_model,
            token_usage_parser=get_token_usage_for_openai,
        )

        return {
            "faithfulness": result["faithfulness"],
            "answer_relevancy": result["answer_relevancy"],
            "answer_correctness": result["answer_correctness"],
            "context_recall": result["context_recall"],
            "context_precision": result["context_precision"],
        }

    async def run_weave_evaluation(self, eval_dataset: Dataset | weave_client.ObjectRef):
        model = self.omni_claude_model

        if isinstance(eval_dataset, Dataset):
            eval_dataset = eval_dataset.to_list()

        evaluation = weave.Evaluation(
            dataset=eval_dataset,
            scorers=[self.evaluate_row],
        )
        results = await evaluation.evaluate(model=model)
        return results


class OmniClaudeModel(Model):
    claude_assistant: ClaudeAssistant

    @weave.op()
    def predict(self, question: str) -> dict:
        return self.claude_assistant.predict_for_evaluation(question)


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
        self.generator = generator or DatasetGenerator(claude_assistant=self.claude_assistant, loader=self.loader)
        self.evaluator = evaluator or Evaluator(claude_assistant=self.claude_assistant)

    @base_error_handler
    async def run_pipeline(
        self,
        generate_new_dataset: bool = False,
        num_questions: int = 5,
        input_filename: str = "docs_anthropic_com_en_20240928_135426.json",
        weave_dataset_name: str = "anthropic_dataset",
    ):
        """Runs evaluation pipeline with pre-determined parameters"""

        if generate_new_dataset:
            logger.info("Generating new dataset...")
            # Generate and upload new dataset
            docs = self.loader.get_documents(filename=input_filename)
            dataset = self.generator.generate_dataset(documents=docs, test_size=num_questions)

            for row in dataset:
                logger.debug(f"Question: {row['question']}")

            # Upload dataset
            await self.weave_manager.upload_dataset(dataset, name="anthropic_dataset")

        # Retrieve dataset from Weave
        dataset = await self.weave_manager.retrieve_dataset(name=weave_dataset_name)
        logger.debug(f"First row of the dataset {dataset.rows[0]}")

        # Run evaluation
        results = await self.evaluator.run_weave_evaluation(eval_dataset=dataset)
        return results


async def main():
    configure_logging()

    load_dotenv()

    filename = "docs_anthropic_com_en_20240928_135426.json"

    pipeline_manager = EvalManager()

    # Run the pipeline
    results = await pipeline_manager.run_pipeline(
        generate_new_dataset=True,
        input_filename=filename,
        num_questions=10,
        weave_dataset_name="anthropic_dataset",
    )

    print("Evaluation Results:")
    pprint(results)


#
if __name__ == "__main__":
    asyncio.run(main())


#
