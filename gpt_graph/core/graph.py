# -*- coding: utf-8 -*-
"""
Created on Sun Jun  2 12:46:36 2024

@author: User
"""

import numpy as np
from gpt_graph.utils.debug import logger_debug, debug

import networkx as nx
import matplotlib.pyplot as plt
from gpt_graph.utils.visualize_graph import visualize_graph
import pprint
from gpt_graph.utils.mql import mql
from gpt_graph.utils.uuid_ex import uuid_ex
import os
from contextlib import contextmanager


class Graph:
    def __init__(self, graph=None, pipeline=None, output_folder=None):
        self.uuid = uuid_ex(obj=self)
        self.graph = graph or nx.DiGraph()
        self.pipeline = pipeline
        self.output_folder = output_folder

    def initialize(self):
        """
        Clear all nodes and reset the graph to its initial state.
        """
        self.graph.clear()

    def default_get_input_nodes(
        self,
        filter_cri=None,
        children=None,
        if_inclusive=False,
        if_output_when_possible=True,
    ):
        """
        Gets input nodes based on filter criteria.

        Args:
            filter_cri (dict): Criteria to filter nodes. Default: None (uses latest step).
            children (list): List of child nodes to consider. Default: None.
            if_inclusive (bool): Include children in filtering. Default: False.
            if_output_when_possible (bool): Default: True.

        Returns:
            list: Filtered nodes.
        """
        if filter_cri is None:
            filter_cri = {"step_id": {"$order": -1}}

        nodes = self.filter_nodes(
            filter_cri,
            children=children,
            if_inclusive=if_inclusive,
        )

        if if_output_when_possible and any(node["if_output"] for node in nodes):
            nodes = [node for node in nodes if node["if_output"]]

        return nodes

    def _node_or_id_to_id_list(self, node_or_id=None):
        """
        A helper func
        Converts node or node ID input to a list of node IDs.

        Args:
            node_or_id (None, node(dict), list of nodes, or id): Node, node ID, or list of nodes/IDs.

        Returns:
            list: List of node IDs.

        Handles None, single nodes (dict), node IDs (str), and lists of nodes/IDs.
        Recursively processes list inputs.
        """
        if node_or_id is None:
            return []

        if isinstance(node_or_id, dict):
            return [node_or_id["node_id"]]
        elif isinstance(node_or_id, list):
            normalized_ids = []
            for item in node_or_id:
                normalized_ids.extend(self._node_or_id_to_id_list(item))
            return normalized_ids
        elif node_or_id in self.graph.nodes():
            return [node_or_id]
        else:
            raise ValueError

    @contextmanager
    def record_changes(self):
        """
        used in Step.run, so that modified nodes during @method_step can be modified afterwards

        Yields:
            dict: Contains 'added_nodes' (list of new node dicts) and 'removed_keys' (list of removed node keys).

        Usage:
            with self.record_changes() as changes:
                # Perform graph operations
            # Access changes after the context
        """
        initial_node_keys = set(self.graph.nodes())
        changes = {"added_nodes": [], "removed_keys": []}

        try:
            yield changes
        finally:
            final_node_keys = set(self.graph.nodes())
            added_keys = final_node_keys - initial_node_keys
            removed_keys = initial_node_keys - final_node_keys

            changes["added_nodes"] = [self.graph.nodes[key] for key in added_keys]
            changes["removed_keys"] = list(removed_keys)

    def add_node(
        self,
        content,
        type=str,  # "string",
        node_id=None,
        name="default",
        step_name="",
        step_id=None,
        level=None,
        parent_nodes=None,
        # group_id=None,
        verbose=True,
        extra={},
        if_output=True,
        **kwargs,
    ):
        """
        Adds a new node to the graph.

        Args:
            content: The content of the node.
            type: Type of the content (default: str).
            node_id: Unique identifier for the node (default: auto-generated).
            name: Name of the node (default: "default").
            step_name: Name of the step (default: "").
            step_id: ID of the step (default: None).
            level: Level in the graph hierarchy (default: auto-calculated).
            parent_nodes: Parent node(s) to connect to (default: None).
            verbose: If True, prints node info (default: True).
            extra: Additional attributes for the node (default: {}).
            if_output: Flag to mark node as output (default: True).
            **kwargs: Additional keyword arguments for node attributes.

        Returns:
            dict: Attributes of the newly added node.

        Adds a node to the graph, connects it to parent nodes if specified, and returns the node's attributes.
        """
        # TODO: logger_debug is messy, try to fix
        # group_id seems not needed

        node_id = node_id or uuid_ex()

        parent_node_ids = self._node_or_id_to_id_list(parent_nodes)
        if len(parent_node_ids) > 0:
            max_level = np.max([self.graph.nodes[i]["level"] for i in parent_node_ids])
            level = max_level + 1
        else:
            level = 0

        node_attrs = {
            "node_id": node_id,
            "content": content,
            "type": type,
            "name": name,
            "level": level,
            # "group_id": group_id,
            "step_name": step_name,
            "step_id": step_id,
            "extra": extra,
            "parent_ids": parent_node_ids,
            "if_output": if_output,
            **kwargs,
        }

        self.graph.add_node(node_id, **node_attrs)

        if verbose:
            logger_debug("Added node:", node_attrs)
            text_str = str(content)
            text_preview = text_str[:20] + "..." if len(text_str) > 20 else text_str
            print(f"\ttext = {text_preview} ({len(text_str)} characters)")

        logger_debug("parent_node_ids:", parent_node_ids)
        logger_debug("node_ids:", node_id)
        logger_debug("node_attrss:", node_attrs)

        for parent_node_id in parent_node_ids:
            self.graph.add_edge(parent_node_id, node_id)

        return self.graph.nodes[node_id]

    @staticmethod
    def get_node_val_by_key(node, key):
        """
        Extracts a nested value from a node using a dot-notation key.

        Args:
            node: Source dictionary or object.
            key: Dot-separated path to the value (e.g., "user.address.city").

        Returns:
            The value at the specified path, or None if not found.

        Example:
            data = {"user": {"name": "Alice", "address": {"city": "New York"}}}
            city = get_node_val_by_key(data, "user.address.city")  # Returns "New York"

        Note:
            Works with both dictionary keys and object attributes.
            used in self.plot and StepGraph.refresh_node_names
        """
        keys = key.split(".")
        d = node
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            elif getattr(d, k, None) is not None:
                d = getattr(d, k)
            else:
                return None

        return d

    def combine_graph(self, other_graph, if_verbose=False):
        """
        Combine another NetworkX graph into this graph.
        Nodes with the same id in both graphs are combined into one.

        Parameters:
        other_graph: networkx.DiGraph
            The other graph to combine with this graph.
        if_verbose: bool, optional (default=False)
            If True, print warnings about duplicate nodes.

        Note:
            curr used in Step.run if output_format is 'graph', it will be combined with step's node_graph
        """
        duplicate_count = 0

        # Update existing nodes with attributes from other_graph
        for node, data in other_graph.nodes(data=True):
            if node in self.graph:
                self.graph.nodes[node].update(data)
                duplicate_count += 1
            else:
                self.graph.add_node(node, **data)

        # Add edges from other_graph
        self.graph.add_edges_from(other_graph.edges(data=True))

        if if_verbose and duplicate_count > 0:
            print(f"Warning: {duplicate_count} duplicate node(s) found and merged.")

    def get_leaf_nodes(self, exclude=[]):
        """
        Finds leaf nodes in the graph.

        Args:
            exclude (list): Node IDs to ignore.

        Returns:
            list: Data of leaf nodes not in exclude list.

        Leaf nodes are those with no successors or only excluded successors.
        """
        exclude_set = set(exclude)
        leaf_nodes = [
            node
            for node in self.graph.nodes
            if all(neighbor in exclude_set for neighbor in self.graph.successors(node))
        ]
        # Collect their node data
        leaf_node_data = [
            self.graph.nodes[node] for node in leaf_nodes if node not in exclude_set
        ]
        return leaf_node_data

    def get_root_nodes(self, exclude=[]):
        """
        Finds root nodes in the graph.

        Args:
            exclude (list): Node IDs to ignore.

        Returns:
            list: Data of root nodes not in exclude list.

        Root nodes are those with no predecessors or only excluded predecessors.
        """
        exclude_set = set(exclude)
        root_nodes = [
            node
            for node in self.graph.nodes
            if all(
                neighbor in exclude_set for neighbor in self.graph.predecessors(node)
            )
        ]
        # Collect their node data
        root_node_data = [
            self.graph.nodes[node] for node in root_nodes if node not in exclude_set
        ]
        return root_node_data

    def filter_nodes(
        self,
        filter_cri={},  # also called filter_cri
        if_inclusive=False,
        children=None,
        parents=None,
    ):
        """
        Filters graph nodes based on attributes and relationships.

        Process:
        1. Finds candidate nodes based on parent/child relationships:
        - If parents specified: selects descendants (and parents if inclusive)
        - If children specified: selects ancestors (and children if inclusive)
        - If both: intersects the two sets
        2. Collects data for candidate nodes
        3. Applies attribute filtering using MQL on collected node data

        Args:
            filter_cri (dict): MQL-style filtering criteria
            if_inclusive (bool): Include parent/child nodes in results
            children (nodes/id or list of nodes/id): Filter by child nodes
            parents (nodes/id or list of nodes/id): Filter by parent nodes

        Returns:
            list: Filtered node data

        Notes:
            - Supports dot notation in attribute keys
            - mql allows $order and $lambda operations. mql is from utils folder. check it for more details
        """
        filter_cri = filter_cri or {}

        if parents is not None:
            candidate_nodes_parents = set()
            parent_ids = self._node_or_id_to_id_list(parents)
            for parent_id in parent_ids:
                if if_inclusive:
                    candidate_nodes_parents.add(parent_id)
                candidate_nodes_parents.update(nx.descendants(self.graph, parent_id))
        else:
            candidate_nodes_parents = set(self.graph.nodes())

        if children is not None:
            candidate_nodes_children = set()
            child_ids = self._node_or_id_to_id_list(children)
            for child_id in child_ids:
                if if_inclusive:
                    candidate_nodes_children.add(child_id)
                candidate_nodes_children.update(nx.ancestors(self.graph, child_id))
        else:
            candidate_nodes_children = set(self.graph.nodes())

        candidate_nodes = candidate_nodes_children.intersection(candidate_nodes_parents)

        nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            if node_id in candidate_nodes:
                nodes.append(node_data)

        # Use mql to filter nodes
        filtered_nodes = mql(nodes, filter_cri)

        return filtered_nodes

    def remove_nodes(self, filter_cri, **kwargs):
        nodes_to_remove = self.filter_nodes(filter_cri, **kwargs)
        for node_attrs in nodes_to_remove:
            node_id = node_attrs.get("node_id")
            if node_id is not None:
                self.graph.remove_node(node_id)
        print(
            f"Removed {len(nodes_to_remove)} nodes matching the attribute dictionary."
        )

    @property
    def nodes(self):
        return self.graph.nodes

    def plot(
        self,
        filter_cri=None,
        if_pyvis=False,
        output_folder=None,
        attr_keys=["node_id", "step_id", "step_name", "name", "type"],
        attr_prefixes={
            "node_id": "n_id",
            "step_id": "s_id",
            "name": "",
            "type": "",
        },
        pyvis_settings={},
        **kwargs,
    ):
        """
        Visualizes the graph using either Pyvis or Matplotlib.

        Args:
            Pyvis:
                if_pyvis (bool): Use Pyvis (True) or Matplotlib (False).
                output_folder (str): Output directory for Pyvis HTML.
                pyvis_settings (dict): Pyvis-specific settings.
            Matplotlib:
                filter_cri (dict): Node filter criteria. None plots all nodes.
                attr_keys (list): Node attributes to display.
                attr_prefixes (dict): Prefixes for attribute labels.
                **kwargs: Additional args for node filtering.

        Functionality:
            - Pyvis: Interactive HTML output.
            - Matplotlib:
                - Nodes: Colored by type, sized by group.
                - Edges: Connections between nodes.
                - Labels: Customizable node information.
                - Legend: Node types.

        Note:
            - Pyvis requires output_folder.
        """
        # TODO: filter_cri/attr_keys/prefixed can be used in Pyvis settings as well. Currently no.

        if if_pyvis:
            output_folder = (
                output_folder
                or self.output_folder
                or os.environ.get("PYVIS_OUTPUT_FOLDER")
            )
            self.output_folder = output_folder

            visualize_graph(
                self.graph,
                output_folder=output_folder,
                # included_attr=attr_keys,
                **pyvis_settings,
            )
        else:
            from collections import Counter

            plt.figure(figsize=(12, 8))  # Set the size of the figure

            if filter_cri is None:
                nodes_to_plot = self.graph.nodes()
            else:
                # Filter the nodes based on the provided filter_cri
                nodes_to_plot = [
                    i["node_id"] for i in self.filter_nodes(filter_cri, **kwargs)
                ]

            level_x = {}
            for node, attr in self.graph.nodes(data=True):
                if node in nodes_to_plot:
                    level = attr["level"]
                    if level not in level_x:
                        level_x[level] = len(level_x)

            # Create a planar layout for the nodes
            # pos = nx.spring_layout(self.graph)
            pos = {}
            for i, (node, attr) in enumerate(self.graph.nodes(data=True)):
                if node in nodes_to_plot:
                    level = attr["level"]
                    pos[node] = (
                        level_x[level],
                        -i,
                    )  # Assign x-coordinate based on level and y-coordinate based on node ID

            node_types = set(self.graph.nodes[node]["type"] for node in nodes_to_plot)

            # Assign colors to each node type
            light_colors = [
                "#FFD1DC",
                "#DAE8FC",
                "#D5E8D4",
                "#FCE8B2",
                "#F8CECC",
                "#D1D1E0",
            ]
            node_colors = {
                node_type: light_colors[i % len(light_colors)]
                for i, node_type in enumerate(node_types)
            }

            # Draw nodes based on type and adjust size based on group size
            for node_type in node_types:
                nodes_of_type = [
                    node
                    for node in nodes_to_plot
                    if self.graph.nodes[node]["type"] == node_type
                ]
                group_sizes = Counter(
                    self.graph.nodes[node]["group_id"] for node in nodes_of_type
                )
                node_sizes = [
                    max(1000 / group_sizes[self.graph.nodes[node]["group_id"]], 100)
                    for node in nodes_of_type
                ]
                nx.draw_networkx_nodes(
                    self.graph,
                    pos,
                    nodelist=nodes_of_type,
                    node_size=node_sizes,
                    node_color=node_colors[node_type],
                )

            # Draw edges
            edges_to_plot = [
                (u, v)
                for u, v in self.graph.edges()
                if u in nodes_to_plot and v in nodes_to_plot
            ]
            nx.draw_networkx_edges(
                self.graph, pos, edgelist=edges_to_plot, width=1.0, alpha=0.7
            )

            # Draw node labels
            labels = {}
            for node in nodes_to_plot:
                attr = self.graph.nodes[node]
                label_parts = []

                for key in attr_keys:
                    # Use the prefix from attr_prefixes if available, otherwise use the key itself
                    prefix = attr_prefixes.get(key, key)
                    value = self.get_node_val_by_key(attr, key)
                    label_parts.append(f"{prefix}: {value}" if prefix else str(value))

                labels[node] = "\n".join(label_parts)

            nx.draw_networkx_labels(self.graph, pos, labels=labels, font_size=10)

            # Add a legend
            legend_handles = [
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor=color,
                    markersize=10,
                    label=node_type,
                )
                for node_type, color in node_colors.items()
            ]
            plt.legend(handles=legend_handles, loc="upper right")
            plt.axis("off")
            plt.show()

    def find_children(self, node_id):
        return list(self.graph.successors(node_id))

    def find_parents(self, node_id):
        return list(self.graph.predecessors(node_id))

    def show_nodes(self, **kwargs):
        """checking func"""
        filtered_nodes = self.filter_nodes(**kwargs)
        pprint.pprint({j["node_id"]: j["type"] for j in filtered_nodes})

    def show_nodes_by_attr(self, attr="step_id", filter_cri={}):
        """
        Displays nodes grouped by a specified attribute. Checking func

        Args:
            attr (str): Attribute to group by. Default: "group_id"
            filter_cri: Filtering criteria for nodes

        Process:
        1. Filters nodes using provided criteria
        2. Groups nodes by specified attribute
        3. Collects type, func_name, and ids for each group
        4. Prints grouped info

        Output format:
        {attr_value}: {'type': type, 'ids': [node_ids]}

        Note: Useful for quick node overview by any attribute
        """
        filtered_nodes = self.filter_nodes(filter_cri)
        attr_dict = {}
        for node_attrs in filtered_nodes:
            attr_value = node_attrs.get(attr)
            node_type = node_attrs.get("type")
            # func_name = node_attrs.get("func_name")
            node_id = node_attrs.get("node_id")

            if attr_value not in attr_dict:
                attr_dict[attr_value] = {"ids": []}

            if "type" not in attr_dict[attr_value]:
                attr_dict[attr_value]["type"] = node_type

            # if "func_name" not in attr_dict[attr_value]:
            # attr_dict[attr_value]["func_name"] = func_name

            attr_dict[attr_value]["ids"].append(node_id)

        for key, value in attr_dict.items():
            print(f"{key}: {value}")

    def save(self, filter_cri=None):
        from gpt_graph.core.closure import Closure

        nodes = self.filter_nodes(filter_cri=filter_cri)

        custom_data = {"nodes": {node["node_id"]: node for node in nodes}}

        Closure.save_elements(
            self, element_type="nodes", filename=None, custom_data=custom_data
        )

    # def get_running_nodes_seq(self, flatten=False):
    #     """
    #     Generate an independent sequence of node data from the graph.

    #     Args:
    #         flatten (bool): Whether to flatten the result list.

    #     Returns:
    #         list: A list of node data in independent sequence order.
    #               If `flatten` is True, the output is a flat list of node data.
    #               Otherwise, it's a nested list where each sublist has node data
    #               from the same level.
    #     """
    #     seq = []
    #     flattern_seq = []
    #     rem_nodes = set(self.graph.nodes)

    #     while rem_nodes:
    #         print("r:", rem_nodes)
    #         # Get root nodes' data excluding already processed nodes
    #         curr_lvl_data = self.get_root_nodes(exclude=flattern_seq)
    #         if not curr_lvl_data:
    #             break  # Avoid infinite loops in case of cyclic dependencies

    #         # Extract names from the node data (assuming each node has a 'name' attribute)
    #         nodes_to_remove = set(data["node_id"] for data in curr_lvl_data)
    #         print("curr_lvl_data:", nodes_to_remove)
    #         seq.append(nodes_to_remove)
    #         flattern_seq.extend(nodes_to_remove)

    #         rem_nodes -= nodes_to_remove

    #     # Flatten the list if required
    #     result = flattern_seq if flatten else seq
    #     return result


# %%


if __name__ == "__main__":
    import pprint

    # Set the output folder
    output_folder = os.environ.get("OUTPUT_FOLDER")

    # Create an instance of Graph
    gm = Graph(output_folder=output_folder)

    # Add some nodes to the graph
    node1 = gm.add_node(content="Start Node", type="entry", name="Start", level=0)

    node2 = gm.add_node(
        content="Process Node",
        type="process",
        name="Process",
        level=1,
        parent_nodes=[node1["node_id"]],
    )
    node3 = gm.add_node(
        content="End Node",
        type="exit",
        name="End",
        level=2,
        parent_nodes=[node2["node_id"]],
    )

    # Show nodes by attribute, focusing on group_id
    gm.show_nodes_by_attr(attr="type")

    # Remove a node based on specific criteria (example criterion: name equals 'Process')
    # gm.remove_nodes({"name": "Process"})

    # Adding additional nodes to demonstrate various functionalities
    node4 = gm.add_node(
        content="Intermediate Node",
        type="intermediate",
        name="Intermediate",
        level=1,
        parent_nodes=[node1["node_id"]],
    )
    node5 = gm.add_node(
        content="Another Process Node",
        type="process",
        name="Process 2",
        level=2,
        parent_nodes=[node4["node_id"]],
    )
    node6 = gm.add_node(
        content="Final Node",
        type="exit",
        name="Final",
        level=3,
        parent_nodes=[node5["node_id"]],
        if_output=True,
    )
    node5 = gm.add_node(
        content="level 1 ",
        type="process",
        name="Process 2",
        level=1,
        parent_nodes=[node4["node_id"]],
    )

    # Example of filtering nodes
    filtered_nodes = gm.filter_nodes({"type": "process", "level": {"$order": -1}})
    pprint.pprint(filtered_nodes)
    # %%
    # Display all nodes using show_nodes function
    print("All nodes:")
    gm.show_nodes()

    # Filtering nodes based on type 'process'
    process_nodes = gm.filter_nodes({"type": "process"})
    print("Process Nodes:", [{node["node_id"]: node["name"]} for node in process_nodes])

    # Identifying and printing input nodes
    input_nodes = gm.default_get_input_nodes()
    print(
        "Input Nodes (default criteria):",
        [{node["node_id"]: node["name"]} for node in input_nodes],
    )

    # Finding children of node4
    children_of_node4 = gm.find_children(node4["node_id"])
    print("Children of Node 4:", children_of_node4)

    # Finding parents of node6
    parents_of_node6 = gm.find_parents(node6["node_id"])
    print("Parents of Node 6:", parents_of_node6)

    # Show nodes by their group_id attribute
    print("Nodes by Group ID:")
    gm.show_nodes_by_attr(attr="group_id")

    # Remove a node and its dependencies (example)
    gm.remove_nodes({"name": "Intermediate Node"})
