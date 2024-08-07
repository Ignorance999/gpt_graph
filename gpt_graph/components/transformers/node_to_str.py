from gpt_graph.core.component import Component
from typing import Any, Dict
from gpt_graph.utils.get_nested_value import get_nested_value


class NodeToStr(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {"node": {"type": "node"}}
    cache_schema = {}
    output_schema = {"result": {"type": str}}
    output_format = "plain"

    @staticmethod
    def run(
        node: Dict[str, Any] = None,
        combined_fields: list[str] = ["content", "extra"],
        separator: str = r"\n",
    ) -> str:
        """
        Convert a single node (dictionary) into a string by combining specified fields.

        Args:
            node (Dict[str, Any], optional): Input node. Defaults to None.
            combined_fields (List[str], optional): List of field names to combine. Can use dot notation for nested fields. Defaults to ["content", "extra"].
            separator (str, optional): String used to join the field values. Defaults to "\\n".

        Returns:
            str: A combined string of the specified fields from the input node.

        Note:
            - If node is None, an empty string is returned.
            - Fields that don't exist in the node or have None value are skipped.
            - All field values are converted to strings before combining.
        """
        if node is None:
            return ""

        field_values = []
        for field in combined_fields:
            # Extract the value using the get_nested_value function
            value = get_nested_value(node, field)
            if value is not None:
                field_values.append(str(value))

        # Join the field values for this node
        combined_str = separator.join(field_values)

        return combined_str


if __name__ == "__main__":
    # Example 1: Basic usage with default settings
    node1 = {"content": "Hello, world!", "extra": "Additional information", "test":"test"}
    result1 = NodeToStr.run(node1)
    print("Example 1 Result:")
    print(result1)
    print()

    # Example 2: Using multiple fields and custom separator
    node2 = {"content": "Node 1", "extra": {"type": "info", "priority": "high"}}
    result2 = NodeToStr.run(
        node2,
        combined_fields=["content", "extra.type", "extra.priority"],
        separator=" | ",
    )
    print("Example 2 Result:")
    print(result2)
    print()

    # Example 3: Handling missing fields and nested structures
    node3 = {
        "content": "Complete",
        "metadata": {"author": "John", "date": "2023-05-01"},
    }
    result3 = NodeToStr.run(
        node3,
        combined_fields=["content", "metadata.author", "metadata.date", "extra.note"],
        separator=", ",
    )
    print("Example 3 Result:")
    print(result3)
    print()

    # Example 4: Empty input
    result4 = NodeToStr.run(None)
    print("Example 4 Result (Empty input):")
    print(result4)
