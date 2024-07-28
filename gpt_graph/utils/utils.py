# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 16:53:41 2024

@author: User
"""

import inspect
import collections
import dataclasses


def serialize_json_recursively(data, ignored_keys=None, included_keys=None):
    """
    Recursively convert non-serializable elements to strings in lists and dictionaries,
    with options to ignore specific keys or include only certain keys.
    """
    if ignored_keys is None:
        ignored_keys = []

    # Helper function to determine if a key should be included
    def should_include(key):
        if included_keys is not None:
            return key in included_keys and key not in ignored_keys
        else:
            return key not in ignored_keys

    if isinstance(data, collections.abc.Mapping):
        return {
            serialize_json_recursively(key): serialize_json_recursively(
                value, ignored_keys
            )  # , included_keys)
            for key, value in data.items()
            if should_include(key)
        }
    elif isinstance(data, list):
        return [
            serialize_json_recursively(item, ignored_keys, included_keys)
            for item in data
        ]
    elif isinstance(data, (str, int, float, bool)) or data is None:
        return data
    elif dataclasses.is_dataclass(data):
        data_dict = dataclasses.asdict(data)
        return {
            key: serialize_json_recursively(value, ignored_keys, included_keys)
            for key, value in data_dict.items()
            if should_include(key)
        }
    else:
        return str(data)


# %%
def truncate_text(text, max_words):
    import re

    # Regular expression to identify Chinese characters
    chinese_char_pattern = re.compile(r"[\u4e00-\u9fff]")

    word_count = 0
    current_length = 0

    # Iterate through each character in the text
    for i, char in enumerate(text):
        if chinese_char_pattern.match(char):
            # If the character is Chinese, increment the word count
            if word_count == max_words:
                break
            word_count += 1
        elif char == " ":
            # If the character is a space, increment the word count for the previous English word
            if word_count == max_words:
                break
            word_count += 1
        elif i == len(text) - 1:
            # If it's the last character in the text and not a space, increment for the last word
            if word_count == max_words:
                break
            word_count += 1

        # Add the character to the current length to be included in the final string
        current_length += 1

    # Return the truncated text
    return text[:current_length]


# Example usage:
if __name__ == "__main__":
    text = "This is a test."
    max_words = 7
    truncated_text = truncate_text(text, max_words)
    print(truncated_text)  # Output should be 'This is a test. 这是一个测'
# %%
import string


def sanitize_filename(filename):
    # Define valid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)

    # Create a new filename by filtering out invalid characters
    sanitized_filename = "".join(c for c in filename if c in valid_chars)

    return sanitized_filename


# %%


def get_func_params(
    func, input_fields=["nodes"], ignore_fields=["self", "kwargs", "args"]
):
    input_fields = set(input_fields or [])
    ignore_fields = set(ignore_fields or [])

    signature = inspect.signature(func)
    params_defaults = {
        param.name: (
            "<INPUT>"
            if param.name in input_fields
            else param.default
            if param.default is not inspect.Parameter.empty
            else "<EMPTY>"
        )
        for param in signature.parameters.values()
        if param.name not in ignore_fields
    }

    return params_defaults


if __name__ == "__main__":
    g = get_func_params(lambda x, y=3: x)


# %%
# @staticmethod
def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    import tiktoken

    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


# %%
def split_text_by_token_count(text, max_token_count, chunk_size):
    split_texts = []
    current_text = ""
    current_token_count = 0

    words = text.split()

    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        chunk_text = " ".join(chunk)
        chunk_token_count = num_tokens_from_string(chunk_text)

        if current_token_count + chunk_token_count > max_token_count:
            split_texts.append(current_text.strip())
            current_text = chunk_text
            current_token_count = chunk_token_count
        else:
            current_text += " " + chunk_text
            current_token_count += chunk_token_count

    if current_text:
        split_texts.append(current_text.strip())

    return split_texts


if __name__ == "__main__":
    s = split_text_by_token_count(
        "eaf wf.feafeaeafafeafafeafffaefaef tewta.--f eraefea wfa ,wr, tetea,wra ,re wtf ,et af ",
        10,
        2,
    )
    print(s)
# %%
# def group_strings_by_token_count(nodes_or_str, max_token_count):
#     # Initialize variables for grouping
#     groups = []
#     current_group = []
#     current_token_count = 0

#     for node in nodes_or_str:
#         if isinstance(node, str):
#             node_text = node
#         else:
#             node_text = node['content']
#         token_count = num_tokens_from_string(node_text)
#         #print("c",token_count)
#         if current_token_count + token_count > max_token_count and current_group:
#             groups.append(current_group)
#             current_group = [node]
#             current_token_count = token_count
#         else:
#             current_group.append(node)
#             current_token_count += token_count
#     if current_group:
#         groups.append(current_group)
#     #print("groups:",groups)
#     return groups
import math


def group_strings_by_token_count(
    nodes_or_str, max_token_count, min_compression_ratio=2
):
    # min_compression_ratio means that if input is list of 5, at most the output will be list of 5/2

    # Initialize variables for grouping
    groups = []
    current_group = []
    current_token_count = 0
    if min_compression_ratio is None:
        target_group_count = len(nodes_or_str)
    else:
        target_group_count = max(
            1, math.ceil(len(nodes_or_str) / min_compression_ratio)
        )

    for node in nodes_or_str:
        if isinstance(node, str):
            node_text = node
        else:
            node_text = node["content"]
        token_count = num_tokens_from_string(node_text)

        # Decide if a new group should start
        if current_token_count + token_count > max_token_count and current_group:
            groups.append(current_group)
            current_group = [node]
            current_token_count = token_count
        else:
            current_group.append(node)
            current_token_count += token_count

    # Add the last group if it has any items
    if current_group:
        groups.append(current_group)

    # Adjust the groups to meet the min_compression_ratio if necessary
    while len(groups) > target_group_count:
        # Find the best two groups to merge based on token counts
        best_pair = None
        best_size = float("inf")
        for i in range(len(groups) - 1):
            combined_tokens = sum(
                num_tokens_from_string(
                    node["content"] if not isinstance(node, str) else node
                )
                for node in groups[i]
            ) + sum(
                num_tokens_from_string(
                    node["content"] if not isinstance(node, str) else node
                )
                for node in groups[i + 1]
            )
            if combined_tokens < best_size:
                best_size = combined_tokens
                best_pair = i

        # Merge the best pair found
        if best_pair is not None:
            groups[best_pair] += groups.pop(best_pair + 1)
        else:
            break

    return groups


if __name__ == "__main__":
    s2 = group_strings_by_token_count(s, 2)
    print(s2)
