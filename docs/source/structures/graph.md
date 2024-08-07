# Graph

Graphs represent the structure of connected components and steps.
- Graph is a wrapper of networkx graph.
- `Graph.graph` is a networkx DiGraph.
- `Pipeline.sub_node_graph` is a Graph that stores nodes created by Steps, containing all the results of running the Steps. For each Component/Step inside the Pipeline, their `node_graph` has the same address as `Pipeline.sub_node_graph`.
- `Pipeline.sub_step_graph` is a StepGraph, inherited from Graph. 

## Important methods

1. `add_node(content, type=str, node_id=None, name="default", step_name="", step_id=None, level=None, parent_nodes=None, verbose=True, extra=None, if_output=True, **kwargs)`
   - Adds a new node to the graph with specified attributes.
   - Connects the new node to parent nodes if provided.
   - Automatically calculates the node's level in the graph hierarchy.
   - Returns the attributes of the newly added node.

2. `filter_nodes(filter_cri={}, if_inclusive=False, children=None, parents=None, relatives=None)`
   - Filters graph nodes based on attributes and relationships.
   - Uses MongoDB-like Query Language (MQL) for attribute filtering.
   - Supports filtering by parent, child, or relative nodes.
   - Allows for complex nested queries and dot notation in attribute keys.
   - Supports custom filtering with `$lambda` and ordering with `$order`.
   - Returns a filtered and ordered list of node data.

3. `plot(filter_cri=None, if_pyvis=False, output_folder=None, attr_keys=["node_id", "step_id", "step_name", "name", "type"], attr_prefixes={...}, pyvis_settings={}, **kwargs)`
   - Visualizes the graph using either Pyvis (interactive HTML) or Matplotlib.
   - Supports node filtering, custom attribute display, and various visualization settings.
   - For Pyvis: Generates an interactive HTML output.
   - For Matplotlib: Creates a static plot with nodes colored by type, sized by group, and labeled with customizable information.

4. `save(filter_cri=None)`
   - Saves the filtered graph nodes to a file.
   - Uses the Closure class to handle the saving process.
   - Filters nodes based on the provided criteria before saving.


## Examples
1. Examples of using `filter_nodes`:
```python
# Filter nodes by attribute
result = graph.filter_nodes({"name": "Node1", "level": {"$gt": 2}})

# Filter nodes by relationship and attribute
result = graph.filter_nodes({"type": "text"}, parents=["parent_node_id"])

# Use custom lambda function and ordering
result = graph.filter_nodes({
    "content": {"$regex": "^important"},
    "level": {"$gt": 1, "$order": 0},
    "extra.score": {"$lambda": lambda x: x > 0.5}
})

# Complex nested query with dot notation
result = graph.filter_nodes({
    "extra.metadata.author": "John Doe",
    "extra.metadata.date": {"$gt": "2023-01-01"}
})
```

2. Example of using `plot`:
```python
# Plot all nodes using Matplotlib
graph.plot()

# Plot filtered nodes using Pyvis
graph.plot(filter_cri={"type": "text"}, if_pyvis=True, output_folder="./output")
```

3. Example of using `save`:
```python
# Save all nodes
graph.save()

# Save only filtered nodes
graph.save(filter_cri={"level": {"$gt": 2}})
```



