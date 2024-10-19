import asyncio
import json
import os.path
from collections.abc import Sequence
from pprint import pprint

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
from ragas.run_config import RunConfig
from ragas.testset import Testset, TestsetGenerator
from ragas.testset.synthesizers import default_query_distribution
from weave import Dataset as WeaveDataset
from weave.trace import weave_client

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
    """DataLoader class to manage loading and saving datasets from/to JSON files."""

    def __init__(self) -> None:
        self.dataset_path = EVAL_DIR
        self.dataset_filename: str = "eval_dataset.json"

    @base_error_handler
    def get_documents(self, filename: str) -> list[Document]:
        """
        Load documents from a specified JSON file.

        Args:
            filename (str): The name of the JSON file to load documents from.

        Returns:
            list[Document]: A list of Document objects loaded from the JSON file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
        """
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
        """
        Update the metadata dictionary with information extracted from the record.

        Args:
            record (dict): A dictionary containing metadata information.
            metadata (dict): A dictionary to be updated with title, url, and description.

        Returns:
            dict: The updated metadata dictionary.

        Raises:
            None
        """
        metadata["title"] = record.get("metadata", {}).get("title", "")
        metadata["url"] = record.get("metadata", {}).get("sourceURL", "")
        metadata["description"] = record.get("metadata", {}).get("description", "")

        return metadata

    @base_error_handler
    def save_dataset(self, dataset: Dataset, filename: str | None = None) -> str:
        """
        Save the dataset to a JSON file.

        Args:
            dataset (Dataset): The dataset to save.
            filename (str | None): The name of the file to save the dataset to. If None, defaults to the class's
            dataset_filename.

        Returns:
            str: The file path where the dataset was saved.

        Raises:
            Exception: If an error occurs while saving the dataset.
        """
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
        """
        Load a dataset from a JSON file.

        Args:
            filename (str, optional): The name of the JSON file to load. Defaults to None.

        Returns:
            Dataset or None: The loaded dataset if successful, None if the file is not found.

        Raises:
            json.JSONDecodeError: If the JSON file is invalid and cannot be decoded.
            Exception: For any other errors encountered while loading the dataset.
        """
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


# TODO: Testset generation fails after migration to 0.2.0
class DatasetGenerator:
    """
    Initialize the DatasetGenerator with configuration, model name, dataset path, and an optional data loader.

    Args:
        run_config (RunConfig): Configuration for the data generation run.
        model_name (str, optional): The name of the model to be used. Defaults to "gpt-4o".
        dataset_path (str, optional): Path to the dataset. Defaults to EVAL_DIR.
        loader (DataLoader, optional): An optional data loader instance. Defaults to None.

    Returns:
        None
    """

    def __init__(
        self,
        run_config: RunConfig,
        model_name: str = "gpt-4o",
        dataset_path: str = EVAL_DIR,
        loader: DataLoader = None,
    ) -> None:
        """
        Initialize the test set generator with configuration and model details.

        Args:
            run_config (RunConfig): Configuration for running the tests.
            model_name (str): Name of the model to be used. Defaults to "gpt-4o".
            dataset_path (str): Path to the dataset. Defaults to EVAL_DIR.
            loader (DataLoader): Optional data loader. Defaults to None.
        """
        self.generator_llm = LangchainLLMWrapper(ChatOpenAI(model=model_name))
        self.generator = TestsetGenerator(llm=self.generator_llm)
        self.dataset_path = dataset_path
        self.dataset: Testset | None = None
        self.loader = loader or DataLoader()
        self.weave_dataset_name: str = "anthropic_dataset"
        self.run_config = run_config or RunConfig()

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], testset_size: int, **kwargs) -> EvaluationDataset:
        """
        Generate an evaluation dataset from documents.

        Args:
            documents (Sequence[Document]): A sequence of Document objects to be used in generating the dataset.
            testset_size (int): The size of the test set to be generated.
            **kwargs: Additional keyword arguments that may be required by the dataset generation process.

        Returns:
            EvaluationDataset: An evaluation dataset created from the generated test dataset.

        Raises:
            ValueError: If the testset_size is invalid or other constraints are not met.
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


# TODO: evaluation run is not refactored to ragas 0.2.0
class Evaluator:
    """
    Evaluate a model's output for a given question and ground truth by computing various metrics.

    Args:
        question (str): The question posed to the model.
        ground_truth (str): The correct answer to the question.
        model_output (dict): The output from the model including the answer and retrieved contexts.

    Returns:
        dict[str, float]: A dictionary containing the computed metric scores.

    Raises:
        ValueError: If the model_output is None.
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
    async def evaluate_row(self, question: str, ground_truth: str, model_output: dict) -> dict[str, float]:
        """
        Evaluate a single question-answer pair using various metrics and return the scores.

        Args:
            question (str): The input question to be evaluated.
            ground_truth (str): The correct reference answer for the question.
            model_output (dict): The model's output containing the predicted answer and context information.

        Returns:
            dict[str, float]: A dictionary where keys are metric names and values are the corresponding
            evaluation scores.

        """
        if model_output is None:
            logger.warning(f"Model output is None for the question: {question[:50]}...")

        sample = SingleTurnSample(
            user_input=question,
            reference=ground_truth,
            response=model_output.get("answer", ""),
            retrieved_contexts=model_output.get("contexts", []),
        )

        # Create a dataset
        eval_dataset = EvaluationDataset(samples=[sample])

        # Initialize metrics
        metrics = list(self.metrics.values())

        # Create embedding model
        embeddings_model = OpenAIEmbeddings(model=self.embedding_model_name)

        result = evaluate(
            dataset=eval_dataset,
            metrics=metrics,
            embeddings=embeddings_model,
            llm=self.evaluator_llm,
            token_usage_parser=get_token_usage_for_openai,
        )

        # TODO: implement support for token usage counting
        # tokens = result.total_tokens()

        # Extract scores
        scores = result.scores[0]

        return {metric: float(score) for metric, score in scores.items()}

    async def run_weave_evaluation(self, eval_dataset: weave_client.ObjectRef) -> dict:
        """
        Run an evaluation using the Weave client.

        Args:
            eval_dataset (weave_client.ObjectRef): The dataset reference for evaluation.

        Returns:
            dict: The evaluation results.

        Raises:
            Exception: If there is an error during the evaluation process.
        """
        logger.info("Running evaluation...")

        evaluation = weave.Evaluation(
            dataset=eval_dataset,
            scorers=[self.evaluate_row],
        )
        results = await evaluation.evaluate(model=self.claude_assistant)
        return results


class WeaveManager:
    """Manages operations related to Weave including initialization, dataset upload, and retrieval."""

    # TODO: refactor WeaveManager out of evaluation module. It should be independent module.

    def __init__(
        self,
        project_name: str = WEAVE_PROJECT_NAME,
    ):
        self.project_name = project_name
        weave.init(project_name)

    def upload_dataset(self, dataset: EvaluationDataset, dataset_name: str) -> str:
        """
        Upload a dataset to the Weave platform.

        Args:
            dataset (EvaluationDataset): The dataset to be uploaded.
            dataset_name (str): The name under which the dataset will be uploaded.

        Returns:
            str: The name of the dataset that was successfully uploaded.

        Raises:
            Exception: If an error occurs during the upload process.
        """
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
        """
        Retrieve a dataset reference by name.

        Args:
            name (str): The name of the dataset to retrieve.

        Returns:
            weave_client.ObjectRef: A reference to the specified dataset.

        Raises:
            ValueError: If the dataset name is not provided.
        """
        if name is None:
            raise ValueError("Dataset name is required!")
        dataset_name = name

        dataset_ref = weave.ref(dataset_name).get()
        print(dataset_ref)
        return dataset_ref


class RAGEvaluationManager:
    """
    Manages dataset generation, uploading, and evaluation processes.

    Args:
        loader (DataLoader, optional): Instance of DataLoader, defaults to None.
        weave_manager (WeaveManager, optional): Instance of WeaveManager, defaults to None.
        vector_db (VectorDB, optional): Instance of VectorDB, defaults to None.
        retriever (ResultRetriever, optional): Instance of ResultRetriever, defaults to None.
        reranker (Reranker, optional): Instance of Reranker, defaults to None.
        generator (DatasetGenerator, optional): Instance of DatasetGenerator, defaults to None.
        evaluator (Evaluator, optional): Instance of Evaluator, defaults to None.
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
        """
        Generate and upload dataset.

        Args:
            input_filename (str): The name of the input file containing documents.
            testset_size (int): The number of examples to include in the test set.

        Returns:
            None

        Raises:
            ValueError: If the dataset generation or upload fails.
        """
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
        """
        Run evaluation on a dataset from Weave asynchronously.

        Args:
            weave_dataset_name (str): The name of the dataset to be retrieved and evaluated.

        Returns:
            dict: The results of the evaluation.

        Raises:
            WeaveRetrievalError: If there is an issue retrieving the dataset from Weave.
            EvaluationError: If there is an error during the evaluation process.
        """
        # Retrieve dataset from Weave
        logger.info(f"Getting a dataset from Weave with name: {weave_dataset_name}")
        dataset = self.weave_manager.retrieve_dataset(name=weave_dataset_name)
        logger.debug(f"First row of the dataset {dataset.rows[0]}")

        # Run evaluation
        results = await self.evaluator.run_weave_evaluation(eval_dataset=dataset)

        # Print the result
        return results


def generate_new_dataset(debug: bool = False):
    """
    Initialize, generate, and upload a new dataset.

    Args:
        debug (bool): If True, enables debug logging. Default is False.

    Returns:
        None

    Raises:
        ConfigurationError: If there's an issue with logging configuration.
        DatasetGenerationError: If there's an issue during dataset generation.
        UploadError: If uploading the dataset fails.
    """
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
    """
    Run the evaluation pipeline asynchronously.

    Args:
        debug (bool): Flag to enable or disable debug logging. Defaults to False.

    Returns:
        None

    Raises:
        Any exceptions that might be raised during the execution of RAGEvaluationManager's run_evaluation_async method.
    """
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
