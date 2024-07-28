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


class Filter(Component, Graph):
    # Class variables
    step_type = "list_to_node"
    input_schema = {
        "nodes": {"type": "node"},
        # "filter_nodes": {"type": Any},
        # "filter_cri": {"type": Dict[str, Any]},
        # "if_ask_user": {"type": bool},
    }
    cache_schema = {}
    output_schema = {"result": {"type": List[Dict]}}
    output_format = "graph"

    def __init__(self, **kwargs):
        # NOTE: have to use super instead of Component, because if using Component, its run method is not self.run, but Component.run
        super().__init__(**kwargs)
        Graph.__init__(self)

    def run(
        self,
        nodes=None,
        filter_nodes=None,
        filter_cri: Dict[str, Any] = None,
        if_ask_user=False,
    ):
        """
        This step filters nodes based on specified criteria. The criteria can be a value for equality check
        or a callable for more complex evaluations.
        """
        # Retrieve input nodes
        # nodes = self.default_get_input_nodes(nodes)
        for node in nodes:
            self.add_node(**node)

        if filter_nodes is None:
            filter_nodes = nodes
        elif validate_type(filter_nodes, "node"):
            pass
        elif isinstance(filter_nodes, dict):
            filter_nodes_raw = filter_nodes.copy()
            # Derive filter_nodes for each node based on some criteria
            filter_nodes = [
                self.default_get_input_nodes(
                    filter_cri=filter_nodes_raw, children=node, if_inclusive=True
                )
                for node in nodes
            ]
            # Flatten the list of lists to a list
            filter_nodes = [item for sublist in filter_nodes for item in sublist]
            if len(filter_nodes) != len(nodes):
                filter_nodes = self.default_get_input_nodes(
                    filter_cri=filter_nodes_raw, if_inclusive=True
                )
        else:
            raise ValueError("Invalid filter_nodes type")

        if len(filter_nodes) != len(nodes):
            raise ValueError(
                f"The number of filter nodes and nodes do not match. "
                f"filter_nodes have: {len(filter_nodes)}; nodes have {len(nodes)}"
            )

        def _match_criteria(self, node, criteria):
            if criteria is None:
                return True
            for key, criterion in criteria.items():
                node_value = self.get_node_val_by_key(key, node)
                if node_value is None:
                    return False
                if callable(criterion):
                    if not criterion(node_value):
                        return False
                else:
                    if node_value != criterion:
                        return False
            return True

        filtered_nodes = []
        for node, filter_node in zip(nodes, filter_nodes):
            if _match_criteria(self, filter_node, filter_cri):
                filtered_nodes.append(node)

        output_nodes = []
        if if_ask_user:
            titles = [
                (
                    node["extra"]["title"]
                    if "title" in node.get("extra", {})
                    else str(node["content"])[:250]
                )
                for node in filtered_nodes
            ]

            selected_indices = multi_select_dialog(
                titles
            )  # TODO: this is for debug only seems there is a bug
            # selected_indices = [1,2,3]
            selected_nodes = [filtered_nodes[i] for i in selected_indices]
        else:
            selected_nodes = filtered_nodes

        for node in selected_nodes:
            output_node = self.add_node(
                content=node["content"],
                type=node.get("type", "generic"),
                name="filtered_node",
                parent_nodes=[node],
                extra=node.get("extra", {}),
            )
            output_nodes.append(output_node)

        return self.graph


# %%
if __name__ == "__main__":
    from gpt_graph.core.pipeline import Pipeline

    p = Pipeline()
    p | Filter()
    test_list = [1, 2, 3, 4, 5]
    filter_criteria = {"content": lambda text: text > 3}
    result = p.run(input_data=test_list, params={"if_ask_user": True})
