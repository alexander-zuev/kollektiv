import os
from pathlib import Path

def generate_project_structure(root_dir, output_file, ignore_dirs=None, ignore_files=None):
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', 'env'}
    if ignore_files is None:
        ignore_files = {'.gitignore', '.env'}

    project_root = Path(root_dir).resolve()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{project_root.name}/\n")
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = len(Path(root).relative_to(project_root).parts)
            indent = '│   ' * (level - 1)
            f.write(f"{indent}├── {os.path.basename(root)}/\n")
            subindent = '│   ' * level
            for file in sorted(files):
                if file not in ignore_files:
                    f.write(f"{subindent}├── {file}\n")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]  # Assumes script is in project_root/scripts/
    output_file = project_root / "scripts" / "project_structure.txt"
    generate_project_structure(project_root, output_file)
    print(f"Project structure has been written to {output_file}")