# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 23:57:41 2024

@author: User
"""

import pandas as pd
from typing import Dict, Callable, Any, List
from gpt_graph.utils.validation import validate_type
from gpt_graph.gui.multi_select_dialog import multi_select_dialog
from gpt_graph.core.component import Component
from gpt_graph.core.graph import Graph
from gpt_graph.utils.mql import mql
import copy
import re


class Filter(Component):
    # Class variables
    step_type = "list_to_list"
    input_schema = {
        "nodes": {"type": "node"},
    }
    cache_schema = {"node_graph": {"key": "<TEMP>", "initializer": "[node_graph]"}}
    output_schema = {"result": {"type": "node"}}
    output_format = "node"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(
        self,
        nodes: List[Dict],
        filter_nodes: List[Dict] = None,
        filter_cri: Dict[str, Any] = None,
        node_graph="<CACHE>",
        if_ask_user: bool = False,
        **placeholders,
    ) -> List[Dict]:
        """
        This step filters nodes based on specified criteria. The criteria can be a value for equality check
        or a callable for more complex evaluations.
        """
        if filter_nodes is None:
            filter_nodes = nodes

        def replace_placeholders(obj, placeholders):
            if isinstance(obj, dict):
                return {
                    key: replace_placeholders(value, placeholders)
                    for key, value in obj.items()
                }
            elif isinstance(obj, list):
                return [replace_placeholders(item, placeholders) for item in obj]
            elif isinstance(obj, str):
                # Check if the entire string is a single placeholder
                match = re.fullmatch(r"\[(\w+)\]", obj)
                if match:
                    placeholder_name = match.group(1)
                    return placeholders.get(placeholder_name, obj)

                # Otherwise, replace placeholders within the string
                def replace_match(match):
                    placeholder_name = match.group(1)
                    return str(placeholders.get(placeholder_name, match.group(0)))

                return re.sub(r"\[(\w+)\]", replace_match, obj)
            return obj

        # Replace placeholders in filter_cri once
        if filter_cri is not None:
            filter_cri = copy.deepcopy(filter_cri)
            filter_cri = replace_placeholders(filter_cri, placeholders)

            # Filter the filter_nodes based on the criteria
            filtered_filter_nodes = mql(filter_nodes, filter_cri)

            # Use node_graph to find the corresponding nodes based on filtered filter nodes
            filtered_nodes, _ = node_graph.filter_connected_node_groups(
                nodes, filtered_filter_nodes
            )
        else:
            filtered_nodes = filter_nodes            

        if if_ask_user:
            titles = [
                node.get("extra", {}).get("title", str(node["content"])[:250])
                for node in filtered_nodes
            ]

            selected_indices = multi_select_dialog(titles)
            selected_nodes = [filtered_nodes[i] for i in selected_indices]
        else:
            selected_nodes = filtered_nodes

        output_nodes = []
        for node in selected_nodes:
            output_node = {
                "content": node["content"],
                "type": node.get("type", "generic"),
                "name": "filtered_node",
                "parent_nodes": [node],
                "extra": node.get("extra", {}),
            }
            output_nodes.append(output_node)

        return output_nodes


# %%
if __name__ == "__main__":
    from gpt_graph.core.pipeline import Pipeline

    p = Pipeline()
    p | Filter()
    test_list = [1, 2, 3, 4, 5]
    filter_criteria = {"content": {"$lambda": lambda text: text > 3}}
    result = p.run(
        input_data=test_list,
        params={"if_ask_user": True, "filter_cri": filter_criteria},
    )
