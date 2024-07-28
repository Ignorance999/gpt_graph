# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 11:58:07 2024

@author: User
"""

import os

import tomli


def load_env(file_path=None):
    """
    Load environment variables from a TOML file and set them in os.environ.

    Args:
    file_path (str): Path to the TOML file.

    Returns:
    dict: A dictionary of the loaded environment variables.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_root = os.path.dirname(current_dir)

    file_path = os.path.join(package_root, "config", "env.toml")

    # Check if the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            toml_string = f.read()

        # Load the TOML file
        config = tomli.loads(toml_string)

        # Iterate through the config and set environment variables
        for key, value in config.items():
            # Convert the value to a string, as environment variables are always strings
            os.environ[key] = str(value)

        # Handle special cases
        if os.environ.get("GPT_GRAPH_FOLDER") == "<NONE>":
            os.environ["GPT_GRAPH_FOLDER"] = package_root
            print(f"GPT_GRAPH_FOLDER is <NONE>, so set to {package_root}")

        if (
            os.environ.get("PYVIS_OUTPUT_FOLDER") == "<NONE>"
            or os.environ.get("OUTPUT_FOLDER") == "<NONE>"
        ):
            output_folder = os.path.join(package_root, "outputs")
            os.environ["PYVIS_OUTPUT_FOLDER"] = output_folder
            os.environ["OUTPUT_FOLDER"] = output_folder
            print(
                f"PYVIS_OUTPUT_FOLDER and OUTPUT_FOLDER are <NONE>, so set to {output_folder}"
            )

        if os.environ.get("TEST_FOLDER") == "<NONE>":
            test_folder = os.path.join(package_root, "tests")
            os.environ["TEST_FOLDER"] = test_folder
            print(f"TEST_FOLDER is <NONE>, so set to {test_folder}")

        print(f"Successfully loaded environment variables from {file_path}")
        return config
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return {}
    except tomli.TomlDecodeError:
        print(f"Error: The file {file_path} is not a valid TOML file.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return {}


# %% doctest
if __name__ == "__main__":
    import doctest

    doctest.testmod()

# %%
# Example usage
if __name__ == "__main__":
    load_env()
    print(os.environ.get("GPT_GRAPH_FOLDER"))
