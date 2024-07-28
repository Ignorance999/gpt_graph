# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 17:07:48 2024

@author: User
"""

import os
from typing import Dict, Any, List
from gpt_graph.core.component import Component
from gpt_graph.core.graph import Graph
import gpt_graph.utils.utils as utils


class Saver(Component):  # Graph
    # Class variables
    # step_type = "list_to_node"
    step_type = "node_to_node"
    input_schema = {
        "node": {"type": "node"},
        # "title_nodes": {"type": "node", "filter_cri": {}},
    }
    cache_schema = {
        "<SELF>": {"key": "[base_name]"},
    }
    output_schema = {"result": {"type": List[str]}}
    output_format = "node_like"  # graph"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Graph.__init__(self)
        self.index = -1

    def run(
        self,
        node: List[Dict],
        title=None,
        output_folder: str = None,
        if_order: bool = True,
        max_title_length: int = 100,
    ) -> List[str]:
        """
        This step saves the content of nodes into text files. Each node is saved as a separate file.
        If 'if_order' is True, filenames are prefixed with their order such as '1_', '2_', etc.
        """

        # for node in nodes:
        # self.add_node(**node)
        self.index += 1
        index = self.index
        # saved_nodes = []
        # for index, node in enumerate(nodes):
        # Construct the filename
        # if isinstance(title, list) and index < len(title):
        #    title = title[index]
        # elif "file_name" in node.get("extra", {}):
        # title = node["extra"]["file_name"]
        # elif "title" in node.get("extra", {}):
        # title = node["extra"]["title"]
        if title is None:
            title = node["content"][:max_title_length]

        title = utils.sanitize_filename(title)
        title = title[:max_title_length].strip()
        file_name = f"{index}_" + title if if_order else title
        file_path = os.path.join(output_folder, file_name + ".txt")

        prefix = node.get("extra", {}).get("prefix", "")
        suffix = node.get("extra", {}).get("suffix", "")
        file_content = prefix + node["content"] + suffix

        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(file_content)

        saved_node = {
            "content": file_path,
            "type": str,
            "name": "saved_file",
            # parent_nodes=node,
        }
        # saved_nodes.append(saved_node)

        return saved_node  # self.graph


if __name__ == "__main__":
    from gpt_graph.core.pipeline import Pipeline

    p = Pipeline()
    p | Saver()

    # Example setup
    output_folder = os.environ.get("OUTPUT_FOLDER")
    os.makedirs(output_folder, exist_ok=True)

    # Example nodes and running the function
    example_nodes = [f"Content of document {i}" for i in range(1, 3)]
    result = p.run(
        input_data=example_nodes,
        params={"output_folder": output_folder, "if_order": True},
    )
    print("Saved files:", result)
