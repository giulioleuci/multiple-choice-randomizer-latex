import os

def ensure_dir(path: str):
    """Creates a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)

def cleanup_latex_files(base_filename: str):
    """Elimina i file temporanei generati da LaTeX."""
    extensions = ['.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk']
    for ext in extensions:
        temp_file = f"{base_filename}{ext}"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
