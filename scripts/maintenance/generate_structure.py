import os
from pathlib import Path


def generate_project_structure(root_dir, output_file, ignore_dirs=None, ignore_files=None):
    """
    Generate a text representation of the directory structure.

    Args:
        root_dir (str): The root directory path to analyze.
        output_file (str): The file where the directory structure should be saved.
        ignore_dirs (set, optional): A set of directory names to ignore. Defaults to commonly ignored directories.
        ignore_files (set, optional): A set of file names to ignore. Defaults to an empty set.

    Returns:
        None.

    Raises:
        IOError: If there is an error opening or writing to the output file.
    """
    if ignore_dirs is None:
        ignore_dirs = {"__pycache__", "venv", "env", ".idea", ".pytest_cache", ".git", ".ruff_cache"}
    if ignore_files is None:
        ignore_files = set()

    project_root = Path(root_dir).resolve()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{project_root.name}/\n")
        first = True
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = len(Path(root).relative_to(project_root).parts)

            if level > 0:  # Skip writing the root directory again
                indent = "│   " * (level - 1)
                f.write(f"{indent}├── {os.path.basename(root)}/\n")
            subindent = "│   " * level

            # Check if we're in the Chroma directory
            in_chroma = "chroma" in Path(root).parts

            for file in sorted(files):
                if file not in ignore_files and not file.endswith(".pyc"):
                    # Only include the database file in the Chroma directory
                    if not in_chroma or file == "chroma.sqlite3":
                        f.write(f"{subindent}├── {file}\n")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    project_root = Path.cwd()  # Use current working directory as root
    output_file = script_dir / "project_structure.txt"

    generate_project_structure(project_root, output_file)
    print(f"Project structure has been written to {output_file}")
