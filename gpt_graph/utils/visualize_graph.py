# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 23:37:04 2024

@author: User
"""

import os
from pyvis.network import Network
import networkx as nx
from gpt_graph.utils.utils import serialize_json_recursively
import matplotlib.pyplot as plt
import matplotlib


def visualize_graph(
    G,
    output_folder,
    ignored_attr=None,
    included_attr=None,
    color_attr=None,
    edge_color_attr=None,
    label_attr=None,
):
    if output_folder is None:
        output_folder = os.environ.get("PYVIS_OUTPUT_FOLDER")

    # if (
    #     color_attr is None
    #     and len(G.nodes) > 0
    #     and "type" in G.nodes[next(iter(G.nodes))]
    # ):
    #     color_attr = "type"

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Path for the output HTML file
    html_file_path = os.path.join(output_folder, "network.html")

    # Initialize Pyvis network with options
    net = Network(height="750px", width="100%", directed=True)
    # Calculate positions based on step_id and node_id
    step_positions = {}
    max_width = 1000  # Example width for positioning
    step_width = 200  # Horizontal distance between steps

    ode_color_map = {}
    edge_color_map = {}
    if color_attr:
        unique_node_values = list(set(nx.get_node_attributes(G, color_attr).values()))
        node_palette = plt.get_cmap("tab20")
        node_color_map = {
            value: node_palette(i / len(unique_node_values))
            for i, value in enumerate(unique_node_values)
        }

    if edge_color_attr:
        unique_edge_values = list(
            set(val for _, _, val in G.edges(data=edge_color_attr) if val is not None)
        )
        edge_palette = plt.get_cmap("tab20b")  # Different palette for distinction
        edge_color_map = {
            value: edge_palette(i / len(unique_edge_values))
            for i, value in enumerate(unique_edge_values)
        }

    # def reorder_dict(d, priority_keys):
    #     """
    #     Reorder a dictionary to put certain keys at the top.

    #     :param d: The input dictionary
    #     :param priority_keys: A list of keys to be placed at the top, in the desired order
    #     :return: A new dict with the specified order
    #     """
    #     # Create a new dict
    #     new_dict = {}

    #     # Add priority keys first, if they exist in the original dict
    #     for key in priority_keys:
    #         if key in d:
    #             new_dict[key] = d[key]

    #     # Add all other items
    #     for key, value in d.items():
    #         if key not in priority_keys:
    #             new_dict[key] = value

    #     return new_dict

    for node, attrs in G.nodes(data=True):
        x = y = None
        if all("step_id" in a for _, a in G.nodes(data=True)):  # All nodes have step_id
            step_id = attrs.get("step_id", 0)
            step_width = 200
            x = step_id * step_width
            y = -list(G.nodes()).index(node) * 100  # Simple vertical stacking

        if color_attr and color_attr in attrs:
            attrs["color"] = matplotlib.colors.rgb2hex(
                node_color_map[attrs[color_attr]]
            )

        if label_attr:
            value = attrs.get(label_attr)
            if value:
                attrs["label"] = value
            else:
                attrs["label"] = "No name: " + attrs.get("uuid", "")

        serialized_attrs = serialize_json_recursively(
            attrs, ignored_keys=ignored_attr, included_keys=included_attr
        )
        # serialized_attrs = reorder_dict(serialized_attrs, ["step_name"])

        # TODO sort the included attr later
        net.add_node(str(node), x=x, y=y, **serialized_attrs)  # s, size=20

    for u, v, attrs in G.edges(data=True):
        if edge_color_attr and edge_color_attr in attrs:
            attrs["color"] = matplotlib.colors.rgb2hex(
                edge_color_map[attrs[edge_color_attr]]
            )
        net.add_edge(str(u), str(v), **attrs)

    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -80000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.1
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "zoomView": true,
        "navigationButtons": true
      }
    }
    """)

    # Save the network as HTML file
    # net.save_graph(html_file_path) false
    net.show(html_file_path, notebook=False)

    # Additional HTML for interactive behavior
    additional_html = """
    <script type="text/javascript">
    document.addEventListener("DOMContentLoaded", function() {
        var infoDiv = document.getElementById("infoDiv");

        function reorderNodeData(nodeData) {
            var priorityKeys = ["node_id", "step_name", "type"];  // Add or remove keys as needed
            var reordered = {};
            
            // Add priority keys first
            for (var i = 0; i < priorityKeys.length; i++) {
                var key = priorityKeys[i];
                if (key in nodeData) {
                    reordered[key] = nodeData[key];
                }
            }
            
            // Add remaining keys
            for (var key in nodeData) {
                if (!priorityKeys.includes(key)) {
                    reordered[key] = nodeData[key];
                }
            }
            
            return reordered;
        }


        network.on("click", function(params) {
          if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            var nodeData = network.body.data.nodes.get(nodeId);

            // Reorder node data
            var reorderedData = reorderNodeData(nodeData);

            var formattedData = JSON.stringify(nodeData, null, 4).replace(/\\\\n/g, '<br>');

            infoDiv.innerHTML = "<h4>Node Details:</h4><pre>" + formattedData + "</pre>";            
            
          } else if (params.edges.length > 0) {
            var edgeId = params.edges[0];
            var edgeData = network.body.data.edges.get(edgeId);
            var formattedEdgeData = JSON.stringify(edgeData, null, 4).replace(/\\\\n/g, '<br>');
            
            infoDiv.innerHTML = "<h4>Edge Details:</h4><pre>" + formattedEdgeData + "</pre>";
          } else {
            infoDiv.innerHTML = "Click on a node or edge to see its attributes.";
          }
        });
    });
    </script>
    <div id="infoDiv" style="position:fixed; top:10px; right:30px; width:500px; height:600px; border:1px solid black; padding:10px; background-color: white;">
    Click on a node or edge to see its attributes.
    </div>
    """

    # The rest of your code where you modify the HTML file remains the same.

    # Modify the HTML after saving to include the custom script and div
    with open(html_file_path, "r") as file:
        html = file.read()

    html = html.replace("</body>", f"{additional_html}</body>")
    # html = html.replace('</head>', '<style>#mynetwork {height: 750px; overflow-y: scroll;}</style></head>')
    with open(html_file_path, "w") as file:
        file.write(html)

    print(f"Graph visualized at {html_file_path}")


# Example usage:
# G = nx.directed_graph()  # or any other way to create a NetworkX graph
# visualize_network(G, 'path/to/output/folder')

# %%
if __name__ == "__main__":
    # Define the path where the HTML file will be saved
    folder_path = os.environ.get("GPT_GRAPH_FOLDER")
    html_file_path = os.path.join(folder_path, "network.html")

    # Create a directed graph with nodes having detailed attributes
    G = nx.DiGraph()
    G.add_node(0, title="Node A", group=1, label="Node A", extra="google", step_id=1)
    G.add_node(1, title="Node B", group=2, label="Node B", extra="facebook", step_id=2)
    G.add_edge(0, 1)
    visualize_graph(G, folder_path)
