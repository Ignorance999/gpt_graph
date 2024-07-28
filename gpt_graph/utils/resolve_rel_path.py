import os
from pathlib import Path
from gpt_graph.utils.load_env import load_env


def resolve_rel_path(path: str) -> str:
    """
    Resolve a relative path to an absolute path.

    If the input is an absolute path, return it unchanged.
    If it's a relative path, prepend it with the GPT_GRAPH_FOLDER environment variable.
    If GPT_GRAPH_FOLDER is not set, attempt to load it from a .env file.

    Args:
        path (str): The input path to resolve.

    Returns:
        str: The resolved absolute path.
    """
    # Convert to Path object for easier manipulation
    p = Path(path)

    # Check if it's an absolute path, regardless of whether it exists
    if p.is_absolute():
        return str(p)

    # Try to get GPT_GRAPH_FOLDER from environment
    base_path = os.environ.get("GPT_GRAPH_FOLDER")

    # If GPT_GRAPH_FOLDER is not set, try to load from .env file
    if base_path is None:
        load_env()
        base_path = os.environ.get("GPT_GRAPH_FOLDER")

    # If still not set, raise an error
    if base_path is None:
        raise ValueError("GPT_GRAPH_FOLDER environment variable is not set")

    # Combine base_path with the relative path and resolve to absolute
    full_path = Path(base_path) / p
    return str(full_path.resolve())


if __name__ == "__main__":
    result = resolve_rel_path(r"./fsfs")
    print(result)
