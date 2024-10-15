# TODO: refactor and separate the dataset generation from evaluation
# TODO: Implement CLI to manage evaluation and dataset generation
# TODO: Upgrade to the new metrics impot

import asyncio
import json
import os.path
from collections.abc import Sequence
from pprint import pprint
from typing import Dict, List, Optional

import weave
from datasets import Dataset
from distlib.markers import Evaluator
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.cost import get_token_usage_for_openai
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextRecall,
    Faithfulness,
    answer_correctness,
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from ragas.testset import Testset, TestsetGenerator, TestsetSample
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
from src.utils.decorators import anthropic_error_handler, base_error_handler
from src.utils.logger import configure_logging, get_logger
from src.vector_storage.vector_db import Reranker, ResultRetriever, VectorDB

logger = get_logger()


class DataLoader:
    """
    Represents a data loader responsible for loading and saving datasets.

    class DataLoader:
        def __init__(self) -> None:
            Initializes the DataLoader with default dataset path and filename.

        @base_error_handler
        def get_documents(self, filename: str) -> list[Document]:
            Loads documents from a JSON file.

            :param filename: Name of the JSON file to load documents from.
            :return: List of Document objects loaded from the file.

        def metadata_func(self, record: dict, metadata: dict) -> dict:
            Extracts basic metadata from a record and updates a metadata dictionary.

            :param record: Dictionary containing the record with metadata.
            :param metadata: Dictionary to update with extracted metadata.
            :return: Updated metadata dictionary.

        @base_error_handler
        def save_dataset(self, dataset: Dataset, filename: Optional[str] = None) -> str:
            Saves the given dataset to a JSON file.

            :param dataset: Dataset object to save.
            :param filename: Optional; Name of the file to save the dataset to. If not provided, uses the default dataset filename.
            :return: Path to the saved dataset file.

        @base_error_handler
        def load_json(self, filename: str = None) -> Dataset | None:
            Loads the dataset from a JSON file.

            :param filename: Optional; Name of the file to load the dataset from. If not provided, uses the default dataset filename.
            :return: Loaded Dataset object if successful, otherwise None.
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
    Class responsible for generating datasets using various language models and embeddings.

    :param model_name: Name of the language model used for generating datasets.
    :type model_name: str, optional
    :param critic_llm: Name of the language model used for critiquing datasets.
    :type critic_llm: str, optional
    :param embedding_model: Name of the embedding model used for datasets.
    :type embedding_model: str, optional
    :param dataset_path: Path where the dataset will be stored.
    :type dataset_path: str, optional
    :param claude_assistant: Instance of ClaudeAssistant for additional functionalities.
    :type claude_assistant: ClaudeAssistant, optional
    :param loader: Instance of DataLoader for loading data.
    :type loader: DataLoader, optional
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        dataset_path: str = EVAL_DIR,
        claude_assistant: ClaudeAssistant = None,
        loader: DataLoader = None,
        weave_manager: WeaveManager = None,
    ) -> None:
        self.generator_llm = LangchainLLMWrapper(ChatOpenAI(model=model_name))
        self.generator = TestsetGenerator(llm=self.generator_llm)
        self.dataset_path = dataset_path
        self.claude_assistant = claude_assistant
        self.dataset: Testset | None = None
        self.dataset_filename: str = "eval_dataset.json"
        self.loader = loader or DataLoader()
        self.weave_dataset_name: str = "anthropic_dataset"

    @base_error_handler
    def generate_dataset(self, documents: Sequence[Document], testset_size: int, **kwargs) -> EvaluationDataset:
        """
        :param documents: A sequence of Document objects to generate the dataset from.
        :type documents: Sequence[Document]
        :param testset_size: The size of the test dataset to be generated.
        :type testset_size: int
        :param kwargs: Additional keyword arguments to pass to the generator.
        :type kwargs: dict
        :return: The generated Dataset object.
        :rtype: Dataset
        """
        query_distribution = default_query_distribution(self.generator.llm)

        test_dataset = self.generator.generate_with_langchain_docs(
            documents=documents,
            testset_size=testset_size,
            query_distribution=query_distribution,
            **kwargs,
        )

        # dataset = self.convert_to_dataset(test_dataset)
        # self.dataset = dataset
        evaluation_dataset = test_dataset.to_evaluation_dataset()
        return evaluation_dataset

    # TODO: Deprecate and remove this method
    @anthropic_error_handler
    def convert_to_dataset(self, test_dataset: Testset) -> EvaluationDataset:
        """Takes synthetic dataset from Ragas and converts to HF Dataset"""
        if not test_dataset:
            raise ValueError("Dataset not generated, generate the dataset first!")

        samples = []
        for sample in test_dataset.samples:
            samples.append(
                SingleTurnSample(
                    user_input=sample.question,
                    response="",  # This will be filled during evaluation
                    retrieved_contexts=sample.contexts,
                    reference=sample.ground_truth,
                )
            )
        return EvaluationDataset(samples=samples)

        #
        # data = {
        #     "user_input": [],
        #     "contexts": [],
        #     "ground_truth": []
        # }
        #
        # for row in test_dataset.samples:
        #     data["user_input"].append(row.user_input)
        #     data["contexts"].append(row.reference_contexts)
        #     data["ground_truth"].append(row.reference)
        #
        # dataset = Dataset.from_dict(data)
        # self.dataset = dataset
        # return self.dataset


class WeaveManager:
    """
    WeaveManager class provides an interface for interacting with Weave for dataset operations.

    Methods
    -------
    __init__(project_name: str = WEAVE_PROJECT_NAME)
        Initializes the WeaveManager with the given project name.

    upload_dataset(dataset: Dataset, name: str) -> str
        Uploads the given HuggingFace dataset to Weave and returns the name of the uploaded dataset.

    retrieve_dataset(name: str) -> weave_client.ObjectRef
        Retrieves a dataset from Weave using the given dataset name and returns a reference to the dataset.
    """

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
    """
    Evaluator class for evaluating model-generated outputs against ground truth answers.

    This class provides methods for evaluating model outputs in terms of several metrics such as faithfulness, answer relevancy, answer correctness, context recall, and context precision. It integrates with various models and datasets to perform comprehensive evaluations.
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

        sample = SingleTurnSample(
            user_input=question,
            reference=ground_truth,
            response=model_output.get("answer", ""),
            retrieved_contexts=model_output.get("contexts", []),
        )

        # answer = model_output.get("answer", "")
        # contexts = model_output.get("contexts", [])

        # if not contexts:
        #     logger.warning(f"No contexts found for question: {question[:50]}...")

        # prepare data for RAGAS
        # data = {
        #     "question": [question],
        #     "ground_truth": [ground_truth],
        #     "answer": [answer],
        #     "retrieved_contexts": [contexts],
        # }

        dataset = Dataset.from_dict(data)

        # initialize metrics

        metrics = [faithfulness, answer_relevancy, answer_correctness, context_recall, context_precision]

        judge_model = ChatOpenAI(model=self.evaluator_model_name)
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
            "context_recall": result["context_recall"],
            "context_precision": result["context_precision"],
        }

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


class EvalManager:
    """
    class EvalManager:
        Initializes an instance of the EvalManager with optional components.

        Parameters:
            loader (DataLoader): An instance of DataLoader, defaults to a new DataLoader instance if not provided.
            weave_manager (WeaveManager): An instance of WeaveManager, defaults to a new WeaveManager instance if not provided.
            vector_db (VectorDB): An instance of VectorDB, defaults to a new VectorDB instance if not provided.
            claude_assistant (ClaudeAssistant): An instance of ClaudeAssistant, defaults to a new ClaudeAssistant instance if not provided.
            retriever (ResultRetriever): An instance of ResultRetriever, defaults to a new ResultRetriever instance if not provided.
            reranker (Reranker): An instance of Reranker, defaults to a new Reranker instance if not provided.
            generator (DatasetGenerator): An instance of DatasetGenerator, defaults to a new DatasetGenerator instance if not provided.
            evaluator (Evaluator): An instance of Evaluator, defaults to a new Evaluator instance if not provided.

    @base_error_handler
    async def run_pipeline:
        Runs evaluation pipeline with pre-determined parameters.

        Parameters:
            generate_new_dataset (bool): Indicates whether to generate a new dataset. Defaults to False.
            num_questions (int): Number of questions for test size in the dataset. Defaults to 5.
            input_filename (str): Name of the input file containing documents. Defaults to "docs_anthropic_com_en_20240928_135426.json".
            weave_dataset_name (str): Name of the dataset in Weave to be used. Defaults to "anthropic_dataset".

        Returns:
            results: The results of the evaluation after running the pipeline.
    """

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
        testsize: int = 5,
        input_filename: str = "docs_anthropic_com_en_20240928_135426.json",
        weave_dataset_name: str = "anthropic_dataset",
    ):
        """Runs evaluation pipeline with pre-determined parameters"""

        if generate_new_dataset:
            logger.info("Generating new dataset...")
            # Generate and upload new dataset
            docs = self.loader.get_documents(filename=input_filename)
            dataset = self.generator.generate_dataset(documents=docs, testset_size=testsize)

            for row in dataset:
                logger.debug(f"Question: {row['question']}")

            # Upload dataset
            await self.weave_manager.upload_dataset(dataset, name="anthropic_dataset")

        # Retrieve dataset from Weave
        logger.info(f"Getting a dataset from Weave with name: {weave_dataset_name}")
        dataset = await self.weave_manager.retrieve_dataset(name=weave_dataset_name)
        logger.debug(f"First row of the dataset {dataset.rows[0]}")

        # Run evaluation
        results = await self.evaluator.run_weave_evaluation(eval_dataset=dataset)
        return results


async def main():
    configure_logging(debug=False)  # Debug mode is OFF

    filename = "docs_anthropic_com_en_20240928_135426.json"

    # Initialize dataset generator and evaluation manager

    # Generate a new dataset or not

    # Run evaluation pipeline on a given dataset

    pipeline_manager = EvalManager()

    # Run the pipeline
    results = await pipeline_manager.run_pipeline(
        generate_new_dataset=True,
        input_filename=filename,
        testsize=1,
        weave_dataset_name="anthropic_dataset",
    )
    await asyncio.sleep(0)  # Give a chance for any lingering tasks to complete

    print("Evaluation Results:")
    pprint(results)


def new_ragas():
    configure_logging(debug=True)  # Debug mode is OFF
    dataset_generator = DatasetGenerator()
    weave_manager = WeaveManager()

    filename = "docs_anthropic_com_en_20240928_135426.json"
    testsize = 5

    logger.info("Generating new dataset...")
    # Generate and upload new dataset
    docs = dataset_generator.loader.get_documents(filename=filename)
    dataset = dataset_generator.generate_dataset(documents=docs, testset_size=testsize)
    print(dataset)

    # Upload the dataset
    weave_manager.upload_dataset(dataset, name="anthropic_dataset_v0.2")


#
if __name__ == "__main__":
    # asyncio.run(main())
    new_ragas()
