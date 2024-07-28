# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 22:27:42 2024

@author: User
"""

from gpt_graph.core.component import Component
import os
import re
from typing import List, Dict


class DirFileLister(Component):
    step_type = "node_to_list"
    input_schema = {"folder_path": {"type": "file_path"}}
    cache_schema = {}
    output_schema = {"file_list": {"type": "file_path"}}
    output_format = "plain"

    def run(
        self, folder_path: str, recursive: bool = False, regex_pattern: str = ""
    ) -> List:
        """
        Returns a list of file names in the specified folder path.

        Args:
            folder_path (str): The path to the folder to search for files.
            recursive (bool): If True, search recursively in subfolders. Defaults to False.
            regex_pattern (str): An optional regular expression pattern to filter files. Defaults to "".

        Returns:
            List[str]: A list of file paths.

        Raises:
            FileNotFoundError: If the specified folder path does not exist.

        Example:
            >>> import os

            >>> file_lister = DirFileLister()
            >>> folder_path = os.environ['TEST_INPUT_FOLDER_PATH']
            >>> result = file_lister.run(
            ...     folder_path=folder_path,
            ...     recursive=True,
            ...     regex_pattern=".*\\.py$"
            ... )
            >>> relative_results = [os.path.relpath(path, folder_path) for path in result]
            >>> relative_results = [p.replace(os.path.sep, '/') for p in relative_results]
            >>> expected_results = [
            ...     'functions_simple_math.py',
            ...     'sample_project/main.py',
            ...     'sample_project/utils/helper.py',
            ...     'sample_project/utils/helper_new.py',
            ...     'sample_project/utils/__init__.py'
            ... ]
            >>> print(f"Files found: {relative_results}")
            Files found: ['functions_simple_math.py', 'sample_project/main.py', 'sample_project/utils/helper.py', 'sample_project/utils/helper_new.py', 'sample_project/utils/__init__.py']
            >>> relative_results == expected_results
            True
        """

        # Check if the folder path exists
        if not os.path.exists(folder_path):
            raise FileNotFoundError(
                f"The specified folder path does not exist: {folder_path}"
            )

        file_list = []
        regex = re.compile(regex_pattern) if regex_pattern else None

        if recursive:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if not regex or regex.search(file):
                        file_list.append(os.path.join(root, file))
        else:
            for file in os.listdir(folder_path):
                full_path = os.path.join(folder_path, file)
                if os.path.isfile(full_path) and (not regex or regex.search(file)):
                    file_list.append(full_path)

        return file_list


# %% doctest
if __name__ == "__main__":
    import doctest

    doctest.testmod()

# %% usage
if __name__ == "__main__":
    file_lister = DirFileLister()
    test_folder = os.environ["TEST_FOLDER"]
    folder_path = test_folder
    result = file_lister.run(folder_path, recursive=True, regex_pattern=".*\\.*$")
    relative_results = [os.path.relpath(path, folder_path) for path in result]
    print(f"Files found: {relative_results}")
