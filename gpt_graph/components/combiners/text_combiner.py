from gpt_graph.core.component import Component
from typing import List, Any


class TextCombiner(Component):
    # Class variables
    step_type = "list_to_node"
    input_schema = {"input_data": {"type": str, "field": "content"}}
    cache_schema = {}
    output_schema = {"result": {"type": str}}
    output_format = "plain"

    @staticmethod
    def run(
        input_data: List[Any] = None,
        separator: str = r"\n",
        id_format: str = None,
        prefix: str = "",
        suffix: str = "",
        max_length: int = None,
    ) -> str:
        """
        Combine list items with optional formatting.

        Args:
            input_data (List[Any]): Items to combine.
            separator (str): Join separator.
            id_format (str): Format for item IDs (e.g., "<{}>: ").
            prefix (str): Text to prepend.
            suffix (str): Text to append.
            max_length (int): Truncate output if exceeded.

        Returns:
            str: Formatted and combined text.

        Example:
            >>> TextCombiner.run(["a", "b"], ", ", "<{}>: ", "Start: ", " :End", 20)
            'Start: <0>: a, <1>: ...'
        """
        if input_data is None:
            return ""

        formatted_items = []
        for index, item in enumerate(input_data):
            formatted_item = str(item)

            if id_format:
                formatted_item = id_format.format(index) + formatted_item

            formatted_items.append(formatted_item)

        combined_text = separator.join(formatted_items)

        if prefix:
            combined_text = prefix + combined_text

        if suffix:
            combined_text = combined_text + suffix

        if max_length and len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."

        return combined_text


if __name__ == "__main__":
    # Example usage
    input_list = ["Hello", "World", "Python"]
    result = TextCombiner.run(
        input_data=input_list,
        separator=" | ",
        id_format="<{}>: ",
        prefix="Start: ",
        suffix=" :End",
        max_length=30,
    )
    print(result)

    # Another example with different parameters
    words = ["Apple", "Banana", "Cherry", "Date"]
    result2 = TextCombiner.run(input_data=words, separator=", ", max_length=20)
    print(result2)
