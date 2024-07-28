# -*- coding: utf-8 -*-
"""
Created on Sun Jun  2 12:46:36 2024

@author: User
"""

import numpy as np
from gpt_graph.utils.debug import logger_debug

import networkx as nx
from gpt_graph.core.graph import Graph


class StepGraph(Graph):
    def add_node(
        self,
        content,
        type=str,  # "string",
        node_id=None,
        name=None,
        level=None,
        parent_nodes=None,
        group_id=None,
        verbose=True,
        extra={},
        edge_type="default",
        **kwargs,
    ):
        """
        override add_node for Graph, as some attr added in Graph is not suitable for StepGraph
        """
        name = name if name is not None else content.name
        node_id = node_id or name  # len(self.graph.nodes())

        parent_node_ids = self._node_or_id_to_id_list(parent_nodes)
        if level is None:
            if len(parent_node_ids) > 0:
                max_level = np.max(
                    [self.graph.nodes[i]["level"] for i in parent_node_ids]
                )
                level = max_level + 1
            else:
                level = 0

        node_attrs = {
            "node_id": node_id,
            "content": content,
            "type": type,
            "name": name,
            "level": level,
            "group_id": group_id,
            "if_output": False,
            "extra": extra,
            "parent_ids": parent_node_ids,
            **kwargs,
        }

        self.graph.add_node(node_id, **node_attrs)

        if verbose:
            logger_debug(f"Added node:", node_attrs)
            text_str = str(content)
            text_preview = text_str[:20] + "..." if len(text_str) > 20 else text_str
            print(f"\ttext = {text_preview} ({len(text_str)} characters)")

        logger_debug("parent_node_ids:", parent_node_ids)
        logger_debug("node_ids:", node_id)
        logger_debug("node_attrss:", node_attrs)

        for parent_node_id in parent_node_ids:
            self.graph.add_edge(
                parent_node_id,
                node_id,
                type=edge_type,
            )

        return self.graph.nodes[node_id]

    def refresh_node_names(self, name_key="name"):
        """
        used in self.combine_graph

        Rename nodes in the graph based on a specified name key.

        Parameters:
        name_key: str, default="name"
            The key in node data used to extract the new name for each node.

        Returns:
        networkx.DiGraph
            A new directed graph with renamed nodes.

        This method creates a new graph where:
        - Each node is renamed based on the value of the specified name_key in its data.
        - The 'name' and 'node_id' attributes of each node are updated to this new name.
        - Edges are preserved and updated to use the new node names.
        - The original graph structure is maintained.

        The method updates self.graph with the new graph and returns it.
        """
        new_graph = nx.DiGraph()
        old_to_new = {}

        # Add nodes with the new names
        for key, data in self.graph.nodes(data=True):
            name = self.get_node_val_by_key(node=data, key=name_key)
            data["name"] = name
            data["node_id"] = name
            old_to_new[key] = name
            new_graph.add_node(name, **data)

        # Add edges with the new node names
        for u, v, data in self.graph.edges(data=True):
            new_u = old_to_new[u]
            new_v = old_to_new[v]
            new_graph.add_edge(new_u, new_v, **data)

        self.graph = new_graph

        return new_graph

    def combine_graph(self, other_graph, first_output_nodes=None):  # node_graph
        """
        eventually used in Step.run, where output_format is graph

        Combine another NetworkX graph into this graph.

        Parameters:
        other_graph: networkx.DiGraph
            The other graph to combine with this graph.
        first_output_nodes: list, optional
            A list of output nodes in self.graph. If None, leaf nodes of self.graph will be used.
        """
        # make sure graph keys are updated
        self.refresh_node_names()
        other_graph.refresh_node_names()

        # Step 1: Check for node name conflicts
        common_nodes = set(self.graph.nodes).intersection(other_graph.nodes)
        if common_nodes:
            raise ValueError(f"Node name conflicts detected: {common_nodes}")

        if first_output_nodes is None:
            first_output_nodes = self.get_leaf_nodes()

        # Step 2: Combine the graphs
        combined_graph = nx.union(self.graph, other_graph.graph)
        self.graph = combined_graph

        # Step 3: Get input nodes from the other graph using get_root_nodes
        input_nodes = other_graph.get_root_nodes()

        # Step 4: Add edges from output nodes to input nodes of other_graph
        for output_node in first_output_nodes:
            for input_node in input_nodes:
                self.graph.add_edge(output_node["node_id"], input_node["node_id"])
                output_node["content"].next = input_node["content"].prev

    def plot(
        self,
        filter_dict=None,
        if_pyvis=False,
        output_folder=None,
        attr_keys=[
            "node_id",
            "content.uuid",
        ],  # "content.input_schema"],  # Only 'id' is needed
        attr_prefixes={},  # Only prefix for 'id'
        pyvis_settings={},
        **kwargs,
    ):
        super().plot(
            filter_dict=filter_dict,
            if_pyvis=if_pyvis,
            output_folder=output_folder,
            attr_keys=attr_keys,
            attr_prefixes=attr_prefixes,
            pyvis_settings=pyvis_settings,
            **kwargs,
        )
