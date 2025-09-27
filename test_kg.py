import os
import ast
import tempfile
import shutil
import git # pip install GitPython

# Assuming hyperon is installed: pip install hyperon-das
from hyperon import MeTTa, E, S

def _clone_repo_to_memory(repo_url: str) -> dict:
    """
    Clones a Git repository to a temporary directory on disk,
    reads all file contents into an in-memory dictionary, and then
    immediately deletes the temporary directory.
    """
    codebase_files = {} 
    temp_dir = tempfile.mkdtemp()
    
    try:
        print(f"Cloning {repo_url} into a temporary location...")
        git.Repo.clone_from(repo_url, temp_dir)
        print("Cloning complete. Reading files into memory...")

        # Walk through the temporary directory and load file contents into the dictionary.
        for root, dirs, files in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, temp_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Store file content in the in-memory dictionary.
                        codebase_files[relative_path] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read file {relative_path}: {e}")

    except git.exc.GitCommandError as e:
        print(f"Error: Failed to clone repository: {e}")
        return {}
    finally:
        # **Crucially, clean up and remove the temporary directory from the disk.**
        print("Deleting temporary directory...")
        shutil.rmtree(temp_dir)
        print("Repository contents are now only in memory.")
        
    return codebase_files

def initialize_codebase_knowledge_graph(metta: MeTTa, codebase_url: str, required_apis: list) -> tuple:
    """
    Clones a repo, builds the KG from its Python files *in memory*,
    and identifies API usage.
    """
    # 1. Get the codebase files into an in-memory dictionary.
    # The _clone_repo_to_memory function handles the temporary clone and cleanup.
    codebase_files = _clone_repo_to_memory(codebase_url)
    if not codebase_files:
        return 0, 0, set()

    project_space = metta.space()
    files_processed = 0
    atoms_added = 0
    verified_apis = set()

    # 2. Iterate over the IN-MEMORY dictionary to build the KG.
    # No further disk access is needed from this point on.
    for relative_path, content in codebase_files.items():
        if relative_path.endswith('.py'):
            try:
                tree = ast.parse(content)
                files_processed += 1
                
                def add_atom_safe(atom):
                    nonlocal atoms_added
                    project_space.add_atom(atom)
                    atoms_added += 1

                for node in ast.walk(tree):
                    # ... (AST parsing logic remains the same)
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        module_name = getattr(node, 'module', None)
                        for alias in node.names:
                            full_import_name = f"{module_name}.{alias.name}" if module_name else alias.name
                            for req_api in required_apis:
                                if req_api in full_import_name.split('.'):
                                    add_atom_safe(E(S("imports_required_api"), S(relative_path), S(req_api)))
                                    verified_apis.add(req_api)
                                    if content.count(f"{req_api}.") > 0 or content.count(f"{alias.asname or alias.name}.") > 0:
                                        add_atom_safe(E(S("uses_api_function"), S(relative_path), S(req_api)))
                    elif isinstance(node, ast.FunctionDef):
                        add_atom_safe(E(S("defines_function"), S(relative_path), S(node.name)))
                    elif isinstance(node, ast.ClassDef):
                        add_atom_safe(E(S("defines_class"), S(relative_path), S(node.name)))
            except Exception as e:
                print(f"Error parsing {relative_path} from memory: {e}")
    
    metta.run('!(add-atom &self (query_pattern find_verified_imports (match &self (imports_required_api $file $module) (pair $file $module))))')
    
    return files_processed, atoms_added, list(verified_apis)

# --- Example Usage ---
if __name__ == "__main__":
    REPO_URL = "https://github.com/ishAN-121/APDP-Implementation"
    REQUIRED_APIS = ["APDP"]

    metta = MeTTa()
    files, atoms, apis = initialize_codebase_knowledge_graph(metta, REPO_URL, REQUIRED_APIS)

    print("\n--- Knowledge Graph Generation Summary ---")
    print(f"Python files processed: {files}")
    print(f"Total atoms added to KG: {atoms}")
    print(f"Verified APIs found: {apis}")