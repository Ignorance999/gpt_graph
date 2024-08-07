from gpt_graph.core.component import Component
from typing import Optional


class TextToBoolParser(Component):
    step_type = "node_to_node"
    input_schema = {"text": {"type": str}}
    cache_schema = {}
    output_schema = {"result": {"type": Optional[bool]}}
    output_format = "plain"

    @staticmethod
    def run(text: str) -> Optional[bool]:
        """
        Parser: This component takes a text input and determines if it's saying True or False.
        It returns None if neither True nor False is found in the text.
        If both are present, it returns the value of the first occurrence.

        :param text: The input text to be parsed
        :return: True, False, or None
        """
        if not isinstance(text, str):
            return None

        text_lower = text.lower()
        true_index = text_lower.find("true")
        false_index = text_lower.find("false")

        if true_index == -1 and false_index == -1:
            return None
        elif true_index == -1:
            return False
        elif false_index == -1:
            return True
        else:
            return true_index < false_index


# Simple test
if __name__ == "__main__":
    test_texts = [
        "TRUE\n\nExplanation: This content provides valuable insights into the company's operations.",
        "FALSE\n\nExplanation: This is a standard form used for individual claims.",
        "This text contains both FALSE and TRUE statements.",
        "This text contains both TRUE and FALSE statements.",
        "This text doesn't contain any boolean indicators.",
    ]

    parser = TextToBoolParser()
    for text in test_texts:
        result = parser.run(text)
        print(f"Input: {text[:50]}...")  # Print first 50 characters
        print(f"Result: {result}")
        print()
