# TODO: refactor and separate the dataset generation from evaluation
# TODO: Implement CLI to manage evaluation and dataset generation
# TODO: Upgrade to the new metrics impot

import asyncio
import json
import os.path
from collections.abc import Sequence
from pprint import pprint
from typing import Optional

import weave
from datasets import Dataset
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.cost import get_token_usage_for_openai
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerCorrectness, AnswerRelevancy, ContextRecall, Faithfulness
from ragas.testset import Testset, TestsetGenerator
from ragas.testset.synthesizers import default_query_distribution
from weave import Dataset as WeaveDataset
from weave.trace import weave_client
from ragas.run_config import RunConfig

from src.generation.claude_assistant import ClaudeAssistant
from src.utils.config import (
    ANTHROPIC_API_KEY,
    EMBEDDING_MODEL,
    EVAL_DIR,
    EVALUATOR_MODEL_NAME,
    MAIN_MODEL,
    RAW_DATA_DIR,
    WEAVE_PROJECT_NAME,
)
from src.utils.decorators import base_error_handler
from src.utils.logger import configure_logging, get_logger
from src.vector_storage.vector_db import Reranker, ResultRetriever, VectorDB

logger = get_logger()


class DataLoader:
    """
    class DataLoader:
        A class used to load, process, and save datasets.

        Methods
        -------
        __init__():
            Initializes the DataLoader with default dataset path and filename.

        get_documents(filename: str) -> list[Document]:
            Loads documents from a JSON file located in RAW_DATA_DIR. Applies metadata processing
            using a specified jq schema and keys.

        metadata_func(record: dict, metadata: dict) -> dict:
            Extracts metadata fields such as title, url, and description from a record and populates
            them into the metadata dictionary.

        save_dataset(dataset: Dataset, filename: str | None = None) -> str:
            Saves the given Dataset object to a JSON file in the specified path. Updates the dataset
            filename if provided and handles errors during the save process.

        load_json(filename: str = None) -> Dataset | None:
            Loads a Dataset from a JSON file. Optionally accepts a filename and updates the default
            dataset filename. Handles different types of loading errors and returns None if the file
            is not found or raises an exception for other errors during the load process.
    """

    def __init__(self) -> None:
        self.dataset_path = EVAL_DIR
        self.dataset_filename: str = "eval_dataset.json"

    @base_error_handler
    def get_documents(self, filename: str) -> list[Document]:
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
    def save_dataset(self, dataset: Dataset, filename: str | None = None) -> str:
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
    """
    :class:`DatasetGenerator`

        An utility class for generating test datasets using a specified language model and dataset path.

        :param model_name: The name of the model to be used for the dataset generation.
        :type model_name: str, optional, default is "gpt-4o"
        :param dataset_path: The path where the dataset is to be stored.
        :type dataset_path: str, default is EVAL_DIR
        :param loader: An instance of DataLoader to load documents, if None a new instance is created.
        :type loader: DataLoader, optional
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        dataset_path: str = EVAL_DIR,
        loader: DataLoader = None,
        run_config: RunConfig = RunConfig() ,
    ) -> None:
        self.generator_llm = LangchainLLMWrapper(ChatOpenAI(model=model_name))
        self.generator = TestsetGenerator(llm=self.generator_llm)
        self.dataset_path = dataset_path
        self.dataset: Testset | None = None
        self.loader = loader or DataLoader()
        self.weave_dataset_name: str = "anthropic_dataset"
        self.run_config = run_config

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], testset_size: int, **kwargs) -> EvaluationDataset:
        """
        :param documents: A sequence of Document objects to be used for dataset generation.
        :param testset_size: The size of the test set to be generated.
        :param kwargs: Additional keyword arguments to be passed to the generator.
        :return: An EvaluationDataset object generated from the input documents.
        """

        query_distribution = default_query_distribution(self.generator.llm)

        test_dataset = self.generator.generate_with_langchain_docs(
            documents=documents,
            testset_size=testset_size,
            query_distribution=query_distribution,
            **kwargs,
        )

        evaluation_dataset = test_dataset.to_evaluation_dataset()
        return evaluation_dataset


class Evaluator:
    """
    Evaluator class for evaluating model-generated outputs against ground truth answers.

    This class provides methods for evaluating model outputs in terms of several metrics such as faithfulness, answer
    relevancy, answer correctness, context recall, and context precision. It integrates with various models and datasets
     to perform comprehensive evaluations.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        embedding_model: str = EMBEDDING_MODEL,
        claude_assistant: ClaudeAssistant = None,
        evaluator_model_name: str = EVALUATOR_MODEL_NAME,
        anthropic_api_key: str = ANTHROPIC_API_KEY,
        claude_assistant_model: str = MAIN_MODEL,
    ):
        self.model_name = model
        self.embedding_model_name = embedding_model
        self.llm = OpenAI(model=model)
        self.embeddings = OpenAIEmbedding(model=embedding_model)
        self.claude_assistant = claude_assistant
        self.evaluator_model_name = evaluator_model_name
        self.evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=evaluator_model_name))
        self.main_model = claude_assistant_model
        self.anthropic_api_key = anthropic_api_key
        self.metrics = self._initialize_metrics()

    def _initialize_metrics(self):
        return {
            "faithfulness": Faithfulness(llm=self.evaluator_llm),
            "answer_relevancy": AnswerRelevancy(llm=self.evaluator_llm),
            "answer_correctness": AnswerCorrectness(llm=self.evaluator_llm),
            "context_recall": ContextRecall(llm=self.evaluator_llm),
            "context_precision": ContextRecall(llm=self.evaluator_llm),
        }

    @weave.op()
    async def evaluate_row(self, question: str, ground_truth: str, model_output: dict) -> dict[str, list[float]]:
        """
        Evaluate a model's output for a given question and ground truth by computing various metrics.

        This method utilizes a dataset containing the question, ground truth, the answer from the model's output,
        and the retrieved contexts to evaluate the performance of the model. It computes several metrics including
        faithfulness, answer relevancy, answer correctness, context recall, and context precision using
        specified evaluation tools.

        :param question: The question posed to the model.
        :type question: str
        :param ground_truth: The expected ground truth answer for the question.
        :type ground_truth: str
        :param model_output: The model's output containing the answer and retrieved contexts.
        :type model_output: dict
        :return: A dictionary with evaluation metric scores.
        :rtype: dict[str, list[float]]
        :raises ValueError: If the model output is None or does not contain necessary keys.
        :raises RuntimeError: If there is an issue with initializing the metrics or models.
        """
        if model_output is None:
            logger.warning(f"Model output is None for the question: {question[:50]}...")

        # sample = SingleTurnSample(
        #     user_input=question,
        #     reference=ground_truth,
        #     response=model_output.get("answer", ""),
        #     retrieved_contexts=model_output.get("contexts", []),
        # )
        #
        # # answer = model_output.get("answer", "")
        # # contexts = model_output.get("contexts", [])
        #
        # # if not contexts:
        # #     logger.warning(f"No contexts found for question: {question[:50]}...")
        #
        # # prepare data for RAGAS
        # # data = {
        # #     "question": [question],
        # #     "ground_truth": [ground_truth],
        # #     "answer": [answer],
        # #     "retrieved_contexts": [contexts],
        # # }
        #
        # dataset = Dataset.from_dict(data)
        #
        # # initialize metrics
        #
        # metrics = [faithfulness, answer_relevancy, answer_correctness, context_recall, context_precision]
        #
        # judge_model = ChatOpenAI(model=self.evaluator_model_name)
        # embeddings_model = OpenAIEmbeddings(model=self.embedding_model_name)
        #
        # result = evaluate(
        #     dataset=dataset,
        #     metrics=metrics,
        #     llm=judge_model,
        #     embeddings=embeddings_model,
        #     token_usage_parser=get_token_usage_for_openai,
        # )
        #
        # return {
        #     "faithfulness": result["faithfulness"],
        #     "answer_relevancy": result["answer_relevancy"],
        #     "context_recall": result["context_recall"],
        #     "context_precision": result["context_precision"],
        # }

    async def run_weave_evaluation(self, eval_dataset: Dataset | weave_client.ObjectRef) -> dict:
        logger.info("Running evaluation...")

        if isinstance(eval_dataset, Dataset):
            eval_dataset = eval_dataset.to_list()

        evaluation = weave.Evaluation(
            dataset=eval_dataset,
            scorers=[self.evaluate_row],
        )
        results = await evaluation.evaluate(model=self.claude_assistant)
        return results


class WeaveManager:
    """
    class WeaveManager:

    """

    def __init__(
        self,
        project_name: str = WEAVE_PROJECT_NAME,
    ):
        self.project_name = project_name
        weave.init(project_name)

    # TODO: refactor to the new evaluation dataset
    def upload_dataset(self, dataset: EvaluationDataset, dataset_name: str) -> str:
        """Uploads dataset to Weave"""
        # Access the list[BaseSample]
        data = dataset.samples

        # Create a Weave Dataset
        weave_dataset = WeaveDataset(name=dataset_name, rows=data)

        try:
            # Publish the dataset
            weave.publish(weave_dataset)

            logger.info(f"Dataset '{dataset_name!r}' uploaded to Weave")
            return dataset_name
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


class RAGEvaluationManager:
    """
    class EvalManager:
        Initializes an instance of the EvalManager with optional components.

        Parameters:
            loader (DataLoader): An instance of DataLoader, defaults to a new DataLoader instance if not provided.
            weave_manager (WeaveManager): An instance of WeaveManager, defaults to a new WeaveManager instance if not
            provided.
            vector_db (VectorDB): An instance of VectorDB, defaults to a new VectorDB instance if not provided.
            claude_assistant (ClaudeAssistant): An instance of ClaudeAssistant, defaults to a new ClaudeAssistant
            instance if not provided.
            retriever (ResultRetriever): An instance of ResultRetriever, defaults to a new ResultRetriever instance
            if not provided.
            reranker (Reranker): An instance of Reranker, defaults to a new Reranker instance if not provided.
            generator (DatasetGenerator): An instance of DatasetGenerator, defaults to a new DatasetGenerator instance
            if not provided.
            evaluator (Evaluator): An instance of Evaluator, defaults to a new Evaluator instance if not provided.

    @base_error_handler
    async def run_pipeline:
        Runs evaluation pipeline with pre-determined parameters.

        Parameters:
            generate_new_dataset (bool): Indicates whether to generate a new dataset. Defaults to False.
            num_questions (int): Number of questions for test size in the dataset. Defaults to 5.
            input_filename (str): Name of the input file containing documents. Defaults to
            "docs_anthropic_com_en_20240928_135426.json".
            weave_dataset_name (str): Name of the dataset in Weave to be used. Defaults to "anthropic_dataset".

        Returns:
            results: The results of the evaluation after running the pipeline.
    """

    def __init__(
        self,
        loader: DataLoader = None,
        weave_manager: WeaveManager = None,
        vector_db: VectorDB = None,
        retriever: ResultRetriever = None,
        reranker: Reranker = None,
        generator: DatasetGenerator = None,
        evaluator: Evaluator = None,
    ):
        self.loader = loader or DataLoader()
        self.weave_manager = weave_manager or WeaveManager()
        self.vector_db = vector_db or VectorDB()
        self.reranker = reranker or Reranker()
        self.retriever = retriever or ResultRetriever(self.vector_db, self.reranker)
        self.dataset_generator = generator
        self.evaluator = evaluator

    @base_error_handler
    def generate_and_upload_dataset(self, input_filename: str, testset_size: int) -> None:
        """Generates a new dataset and uploads it to Weave"""

        logger.info("Generating new dataset...")

        # Generate nodes and metadata
        docs = self.dataset_generator.loader.get_documents(filename=input_filename)

        # Generate a dataset
        dataset = self.dataset_generator.generate_dataset(documents=docs, testset_size=testset_size)
        print(dataset)

        # Upload the dataset to Weave
        dataset_name = "anthropic_dataset_v0.2"
        self.weave_manager.upload_dataset(dataset=dataset, dataset_name=dataset_name)

    @base_error_handler
    async def run_evaluation_async(self, weave_dataset_name: str) -> dict:
        # Retrieve dataset from Weave
        logger.info(f"Getting a dataset from Weave with name: {weave_dataset_name}")
        dataset = self.weave_manager.retrieve_dataset(name=weave_dataset_name)
        logger.debug(f"First row of the dataset {dataset.rows[0]}")

        # Run evaluation
        results = await self.evaluator.run_weave_evaluation(eval_dataset=dataset)

        # Print the result
        return results


def generate_new_dataset(debug: bool = False):
    # Initialize
    configure_logging(debug=debug)
    dataset_generator = DatasetGenerator()
    evaluation_manager = RAGEvaluationManager(generator=dataset_generator)

    # Create & upload
    evaluation_manager.generate_and_upload_dataset(
        input_filename="docs_anthropic_com_en_20240928_135426.json",
        testset_size=5,
    )


async def run_evaluation_pipeline_async(debug: bool = False):
    # Initialize
    configure_logging(debug=debug)
    evaluation_manager = RAGEvaluationManager()

    # Run evaluation
    results = await evaluation_manager.run_evaluation_async(weave_dataset_name="anthropic_dataset_v0.2")

    # Print the results
    print("Evaluation Results:")
    pprint(results)


if __name__ == "__main__":
    # Generate a new dataset
    generate_new_dataset(debug=True)

    # If you have asynchronous evaluation, you can run it separately
    asyncio.run(run_evaluation_pipeline_async(debug=True))