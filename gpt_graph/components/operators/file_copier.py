import os
import shutil
from gpt_graph.core.component import Component
from typing import Optional


class FileCopier(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"source_path": {"type": str, "field": "content"}}
    cache_schema = {}
    output_schema = {"result": {"type": str}}
    output_format = "plain"

    @staticmethod
    def run(source_path: str, dest_folder: str, new_name: Optional[str] = None) -> str:
        """
        Copy a file from one location to another with optional renaming.

        Args:
            source_path (str): The full path of the source file to be copied.
            dest_folder (str): The directory where the file should be copied to.
            new_name (str, optional): The new name for the file. If None, keep the original name.

        Returns:
            str: The full path of the copied file.

        Raises:
            FileNotFoundError: If the source file doesn't exist.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        original_filename = os.path.basename(source_path)

        if new_name is not None:
            # If new_name is provided, use it (keeping the original extension)
            file_extension = os.path.splitext(original_filename)[1]
            new_filename = new_name + file_extension
        else:
            # If new_name is None, keep the original filename
            new_filename = original_filename

        destination_path = os.path.join(dest_folder, new_filename)

        shutil.copy2(source_path, destination_path)

        return destination_path


if __name__ == "__main__":
    # Example usage
    test_folder = os.environ.get("TEST_FOLDER")
    source_file = os.path.join(test_folder, "inputs", "what_is_singularity.txt")
    dest_folder = os.path.join(test_folder, "outputs")

    # Example 1: Move file without renaming
    result = FileCopier.run(source_path=source_file, dest_folder=dest_folder)
    print(f"File moved to: {result}")

    # Example 2: Move file with a new name
    result = FileCopier.run(
        source_path=source_file, dest_folder=dest_folder, new_name="new_file"
    )
    print(f"File moved and renamed to: {result}")

    # Example 3: Handle non-existent file
    try:
        FileCopier.run(source_path="/non/existent/file.txt", dest_folder=dest_folder)
    except FileNotFoundError as e:
        print(f"Error: {e}")
