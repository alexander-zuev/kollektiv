from pprint import pprint

from llama_index.readers.github import GithubClient, GithubRepositoryReader

from src.utils.config import GITHUB_TOKEN

client = github_client = GithubClient(github_token=GITHUB_TOKEN, verbose=False)

reader = GithubRepositoryReader(
    github_client=github_client,
    owner="Twist333d",
    repo="rag-docs",
    use_parser=False,
    verbose=True,
    filter_directories=(
        ["src", "scripts"],  # Include directories you want to index
        GithubRepositoryReader.FilterType.INCLUDE,
    ),
    filter_file_extensions=(
        [
            ".py",  # Include Python files
            ".md",  # Include Markdown files
            ".txt",  # Include text files
        ],
        GithubRepositoryReader.FilterType.INCLUDE,
    ),
)

documents = reader.load_data(branch="main")
pprint(documents)

document_ids = [doc.id_ for doc in documents]
print(document_ids)
