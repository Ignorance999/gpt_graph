from gpt_graph.core.component import Component
from typing import Optional


class PromptFormatter(Component):
    # Class variables
    step_type = "node_to_node"
    input_schema = {
        "field1": {"type": str},
    }
    cache_schema = {}
    output_schema = {"result": {"type": str}}
    output_format = "plain"

    def __init__(self):
        super().__init__()

    def run(
        self,
        prompt: str,
        field1: Optional[str] = None,
        field2: Optional[str] = None,
        field3: Optional[str] = None,
        field_name1: str = "field1",
        field_name2: str = "field2",
        field_name3: str = "field3",
    ) -> str:
        """
        Format a prompt string with provided non-None field values.

        Args:
            prompt: String with placeholders for field values.
            field1, field2, field3: Optional values to insert into the prompt.
            field_name1, field_name2, field_name3: Custom names for fields.

        Returns:
            Formatted string.

        Example:
            formatter = PromptFormatter()
            result = formatter.run(
                prompt="{animal} jumps over {object}",
                field1="fox", field2="fence", field_name1="animal", field_name2="object"
            )
            # Result: "fox jumps over fence"
        """
        format_dict = {}
        if field1 is not None:
            format_dict[field_name1] = field1
        if field2 is not None:
            format_dict[field_name2] = field2
        if field3 is not None:
            format_dict[field_name3] = field3

        return prompt.format(**format_dict)


if __name__ == "__main__":
    # Simple test
    formatter = PromptFormatter()
    test_result = formatter.run(
        prompt="The {animal} jumps over the {object}.",
        field1="fox",
        field2="fence",
        field_name1="animal",
        field_name2="object",
    )
    print("Test result:", test_result)
    assert test_result == "The fox jumps over the fence.", "Test failed!"
    print("Test passed successfully!")

    # Test with a None field
    test_result2 = formatter.run(
        prompt="The {animal} jumps over the {object} under the {location}.",
        field1="fox",
        field2="fence",
        field3=None,
        field_name1="animal",
        field_name2="object",
        field_name3="location",
    )
    print("Test result 2:", test_result2)
    assert test_result2 == "The fox jumps over the fence under the .", "Test failed!"
    print("All tests passed successfully!")
