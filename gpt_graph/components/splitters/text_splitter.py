# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 11:45:47 2024

@author: User
"""

from gpt_graph.utils.utils import (
    num_tokens_from_string,
)  # Importing the token counting function
from gpt_graph.core.component import Component


class TextSplitter(Component):
    step_type = "node_to_list"
    input_schema = {"text": {"type": str}}
    output_schema = {"segment": {"type": str}}

    def run(self, text: str, splitter="\n", max_tokens: int = 1000) -> list:
        """
        Splits the text into segments without exceeding the specified number of tokens per segment.
        Each segment will attempt to be as close as possible to the max_tokens limit without exceeding it.
        """
        text = text.encode("utf-8", "ignore").decode(
            "utf-8", "ignore"
        )  # clean the code
        text = text.replace("\x00", "").replace("\u0000", "")

        if max_tokens is None:
            return [text]

        paragraphs = text.split(splitter)  # Splitting text into paragraphs by new lines
        segments = []
        current_segment = []
        current_token_count = 0

        for paragraph in paragraphs:
            num_tokens = num_tokens_from_string(paragraph)
            if current_token_count + num_tokens > max_tokens:
                # If adding this paragraph exceeds max_tokens, start a new segment
                segments.append(splitter.join(current_segment))
                current_segment = []  # Reset current segment
                current_token_count = 0  # Reset token count

            # Add the paragraph to the current segment
            current_segment.append(paragraph)
            current_token_count += num_tokens

        # Don't forget to add the last segment if it's not empty
        if current_segment:
            segments.append(splitter.join(current_segment))

        return segments


if __name__ == "__main__":
    # Example usage:
    splitter = TextSplitter()

    # Using default empty text and max_tokens
    # default_result = splitter.run()
    # print("Default call result:", default_result)

    # Using specific text and max_tokens
    text = (
        "Here is paragraph one.\n\u0000Here is paragraph two.\nHere is paragraph three."
    )
    specific_result = splitter.run(text)
    print("Specific call result:", specific_result)
