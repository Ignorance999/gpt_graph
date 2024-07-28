from gpt_graph.core.component import Component
from typing import Any


class InputInitializer(Component):
    step_type = "node_to_list"
    input_schema = {"input_data": {"type": Any}}
    cache_schema = {}
    output_schema = {"result": {"type": Any}}
    output_format = "node_like"  # "dict",

    # @classmethod
    # @staticmethod
    def run(
        self,
        input_data=None,
        input_type=str,
        input_name="input",
        input_format="plain",  # or plain
        # input_format="plain",  # or "dict", which will dispatch to different steps.
    ):
        nodes = []

        if input_data is None:
            return nodes

        if input_format == "dict" and isinstance(input_data, dict):
            result = []
            for k, v in input_data.items():
                sub_result = self.run(
                    input_data=v,
                    input_type=input_type,
                    input_name=k,
                )
                if isinstance(sub_result, list):
                    result.extend(sub_result)
                else:
                    result.append(sub_result)
            return result

        if not isinstance(input_data, (list, tuple)):
            input_data = [input_data]

        if isinstance(input_data, (list, tuple)):
            for idx, item in enumerate(input_data):
                if isinstance(item, dict) and ("content" in item):
                    node = {
                        "content": item["content"],
                        "extra": item.get("extra", None),
                        "type": input_type,
                        "name": input_name,
                        "parent_nodes": item,
                    }
                    nodes.append(node)
                else:
                    node = {
                        "content": item,
                        "extra": {},
                        "type": input_type,
                        "name": input_name,
                    }
                    nodes.append(node)

        return nodes
