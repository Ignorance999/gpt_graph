# -*- coding: utf-8 -*-
"""
Created on Sat Mar 30 23:46:05 2024

@author: User
"""

from typing import List, Callable, Type, Any

# from pydantic import parse_obj_as
from pydantic import TypeAdapter, HttpUrl
from pathlib import Path
from typing import Optional, TypedDict


# %#%%
from typing import Any, Dict, Union, List


def validate_nodes(nodes, criteria=None, type_hint=None):
    def is_valid_node(node, criteria: Dict[str, Any], type_hint) -> bool:
        # Check if node is of the correct type
        result = True

        if type_hint:
            result = validate_type(
                value=node.get("content"), type_hint=type_hint, if_apply_list=False
            )

        if criteria:
            result = result and all(
                node.get(key) == value for key, value in criteria.items()
            )

        return result

    if isinstance(nodes, list):
        return [is_valid_node(node, criteria, type_hint) for node in nodes]
    elif isinstance(nodes, dict):
        return is_valid_node(nodes, criteria, type_hint)
    else:
        raise ValueError(
            "The nodes argument must be a dictionary or a list of dictionaries."
        )


import regex


def validate_type(
    value: Any, type_hint: Type[Any], if_apply_list: bool = True
) -> Union[List[bool], bool]:
    """
    Validates the type of a given value against a specified type hint.

    This function can handle various types of validations, including custom types like 'node', 'node_like', and 'file_path'.
    It can also validate each element of a list if the input is a list and if_apply_list is True.

    Parameters:
    - value (Any): The value to be type-checked.
    - type_hint (Type[Any]): The expected type or a string representing a custom type ('node', 'node_like', 'file_path').
    - if_apply_list (bool, optional): If True and value is a list, validates each element of the list. Defaults to True.

    Returns:
    - Union[List[bool], bool]:
        - If value is a list and if_apply_list is True, returns a list of booleans indicating the validity of each element.
        - Otherwise, returns a single boolean indicating whether the value matches the type hint.

    Custom type validations:
    - 'node': Checks if the value is a dict with keys ['node_id', 'type', 'name', 'content', 'step_id'].
    - 'node_like': Checks if the value is a dict with keys ['content', 'extra'].
    - 'file_path': Checks if the value is a valid Windows file path.

    For other types, it uses Pydantic's TypeAdapter for validation.

    Note: This function uses helper methods `has_required_keys` and `is_file_path` for custom type validations.
    """

    def has_required_keys(
        nodes: Union[List[Dict], Dict], required_keys: List[str]
    ) -> bool:
        if isinstance(nodes, list):
            return all([has_required_keys(node, required_keys) for node in nodes])
        elif isinstance(nodes, dict):
            return all(key in nodes for key in required_keys)
        else:
            return False

    def is_file_path(path: str) -> bool:
        # Windows file path pattern (e.g., C:\Folder\file.txt)
        pattern = r"^[a-zA-Z]:\\(?:[^\\\/:*?\"<>|\r\n]+\\)*[^\\\/:*?\"<>|\r\n]*$"
        return regex.match(pattern, path) is not None

    if isinstance(value, list) and if_apply_list:
        # Validate each element in the list and return a list of bools
        return all(
            [validate_type(item, type_hint, if_apply_list=False) for item in value]
        )
    else:
        if type_hint == "node":
            return has_required_keys(
                value, ["node_id", "type", "name", "content", "step_id"]
            )
        elif type_hint == "node_like":
            return has_required_keys(value, ["content", "extra"])
        elif type_hint == "file_path":
            return is_file_path(value)
        else:
            try:
                # Assuming TypeAdapter is defined elsewhere that wraps Pydantic functionality
                ta = TypeAdapter(type_hint)
                ta.validate_python(value)
                # parse_obj_as(type_hint, value) - commented out, assuming it's replaced by TypeAdapter
                return True
            except:
                return False


if __name__ == "__main__":
    print(validate_type("ee", str))
    print(validate_type(3.2, int))
    print(validate_type(3.0, int))
    print(validate_type({55: 1}, dict))

    print(
        validate_type(
            r"./test/test.py",
            "file_path",
        )
    )
    print(validate_type(r"https://docs.pydantic.dev/latest/api/networks/", HttpUrl))

    print(validate_type("fefwfwfa", Path))

    node_data = {
        "id": 3,
        "content": "dd",
        "type": str,
        "name": "dd",
        "group_id": 4,
        "step_id": 5,
    }

    print(validate_type(node_data, "node"))

    type_hint = int

    # Provide the value you want to validate
    value_to_check = [{"content": 3}, {"content": 5}]

    # Call the function with the new parameter names
    # result = validate_type(value_to_check,
    #                        type_hint,
    #                        if_allow_node_extract=True,
    #                        if_allow_list_extract=True)
    # print(result)
# %%
