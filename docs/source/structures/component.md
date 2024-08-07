# Component

Components are the building blocks of our pipeline system. There are three ways to create a Component:

1. **Class-based Component** (Component.category: "class" or "static")
   Inherit from the `Component` class in `gpt_graph.core.component`:

   ```python
   class CustomComponent(Component):
       step_type = "node_to_list"
       input_schema = {"source_url": {"type": str}}
       cache_schema = {}
       output_schema = {"video_data": {"type": "list"}}
       output_format = "node_like"
   ```

2. **Decorator-based Static Component** (Component.category: "static")
   Use the `@component` decorator from `gpt_graph.decorators.component`:

   ```python
   @component(step_type="list_to_node")
   def f5(x):
       return np.sum(x)
   ```

3. **Method-based Component** (Component.category: "method")
   Define the component as a method inside a Pipeline class, still using the `@component` decorator.

## Component Categories

The `Component.category` determines how the function will be executed when wrapped inside a Step:

- **"class"**: The Step initiates the component as a class and calls `cp.run()`.
- **"static"**: The Step directly calls the static function inside the Component.
- **"method"**: The Step plugs in `self` as the current running Pipeline, so the method runs as if bound to the Pipeline.

## Pipeline Execution

When `Pipeline.run()` is called:
1. Components in the pipeline are checked against their criteria (bindings) or the last running step's criteria (linkings).
2. If criteria are met, Steps are created by the Component. Then Steps will be insert into Pipeline's priority queue Pipeline.sub_steps_q
3. If Component.category is 
- static. That means Component.run is a static method, it will be run during Step.run
- class. During Step.run, a new Component will be created and its run method will be called. 
**important**, so Component create Step and then Step will also create several Components using Component.clone() and eventually run them.
- method. This Component's self is bound to the outside Pipeline, therefore it can get access to all the Pipeline's methods and data, including Pipeline.route_to. 
3. Steps run according to their priorities, adding nodes to `Pipeline.sub_node_graph` (a wrapper of a networkx graph).

## Step type
There are several possible values: "node_to_list", "list_to_node", "node_to_node" and "list_to_list"
The main idea is, each previous Step will produce a list of nodes. How should the next Step process it? It can use "group" mode or "apply" mode.
e.g.
1. sum should use "list_to_node"
2. split should use "node_to_list"
3. if you want to multiply each node content by 2, use "node_to_node"
4. filter should use "list_to_list"

The step_type of a Component directly influences the dim (dimension) key in its input_schema. This relationship can be summarized as follows:

- If step_type is "node_to_x" (where x can be node or list), then dim is typically ≥ 0.
- If step_type is "list_to_x" (where x can be node or list), then dim is typically -1.

## Input Schema

The Component.input_schema defines how input data is processed. For example:
```python
input_schema = {
    "y": {
        "type": Any,
        "field": "extra.haha",
        "dim": 0,
        "group": g,
        "filter_cri": {"step_name": {"$regex": "f6", "$order": -1}}
    }
}
```
"y" here is the parameter name of the Component.run. In Step.run, parameters and previous Step's nodes will be processed and plugged into Component.run. 

Key concepts:
### dim
Determines how input nodes are processed.
  - `-1`: All nodes from the previous step are input as a list.
  - `≥0`: The Component runs multiple times, once for each node.

Note: When multiple inputs have the same dimension, they should have the same number of elements. If they do not have the same number of elements, they will be pruned/duplicated until the numbers are the same.

#### Example

Consider a Component with the following input schema:

```python
input_schema = {
    "x": {"dim": 0, "field": "content", "filter_cri": {"step_name": {"$regex": "step_x", "$order": -1}}},
    "y": {"dim": 0, "field": "content", "filter_cri": {"step_name": {"$regex": "step_y", "$order": -1}}},
}
```

After applying the `filter_cri` for each parameter, let's assume we have the following filtered nodes:

```python
# Filtered nodes for x
x_nodes = [
    {"node_id": "001", "content": 1, "step_name": "step_x"},
    {"node_id": "002", "content": 2, "step_name": "step_x"},
    {"node_id": "003", "content": 3, "step_name": "step_x"},
    {"node_id": "004", "content": 4, "step_name": "step_x"}
]

# Filtered nodes for y
y_nodes = [
    {"node_id": "101", "content": 10, "step_name": "step_y", "parent_ids": ["001", "003"]},
    {"node_id": "102", "content": 20, "step_name": "step_y", "parent_ids": ["002"]}
]
```

Here's how the inputs would be processed:

1. First, `x` and `y` are aligned based on their relationships:

   ```python
   x: [
       {"node_id": "001", "content": 1, "step_name": "step_x"},
       {"node_id": "003", "content": 3, "step_name": "step_x"},
       {"node_id": "002", "content": 2, "step_name": "step_x"}
   ]
   y: [
       {"node_id": "101", "content": 10, "step_name": "step_y", "parent_ids": ["001", "003"]},
       {"node_id": "101", "content": 10, "step_name": "step_y", "parent_ids": ["001", "003"]},
       {"node_id": "102", "content": 20, "step_name": "step_y", "parent_ids": ["002"]}
   ]
   ```

   Note that:
   - `x` nodes are reordered to match the parent relationships in `y`.
   - The node with `node_id: "004"` from `x` is discarded as it has no corresponding `y` node.
   - The node with `node_id: "101"` from `y` is duplicated to match its two parent nodes in `x`.

2. Then, the `field` specified in the `input_schema` is used to extract the actual input values:

   ```python
   x_values = [1, 3, 2]
   y_values = [10, 10, 20]
   ```

3. The Component will run three times with the following inputs. The results are will be stored in both the Step and Pipeline.sub_node_graph as nodes(dict)

   ```python
   Run 1: f(x=1, y=10)
   Run 2: f(x=3, y=10)
   Run 3: f(x=2, y=20)
   ```

### group
Groups, created by `Group()`, are used to plug values into function parameters:

```python
g = Group(
    filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
    parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
)
s.p6 = s.f4 | s.f6 | s.f5.prepend(g)
```

In this example:

#### For the Group g:

1. **Parent Node Selection**:
   - Selects nodes with `step_name` matching the regex pattern "f4".
   - `"$order": -1` selects the last (most recent) matching node if multiple nodes match.

2. **Child Node Filtering**:
   - Filters for nodes with `step_name` matching the regex pattern "f6".
   - `"$order": -1` selects the most recent matching node.

3. **Expected Output**:
   When the Group's `run()` method is called, it produces a structured output:
   - A list of Group objects (stored in `self.contains`).
   - Each Group contains "f6" nodes that are children of a specific "f4" node.

   Example structure:
   ```
   [
     sub-group1 containing [f6_1, f6_2],  # Children of f4_1
     sub-group2 containing [f6_3, f6_4, f6_5]  # Children of f4_2
   ]
   ```

#### Pipeline Execution:

1. `g` is prepended to Component `s.f5` in Pipeline `s.p6`.
2. When `s.p6.run()` is called, after running `p6;f4.0`, a new Step `p6;f5.0` is created and calls `g`.
3. `g` returns a list of lists of nodes (e.g., 6 lists of 5 nodes each).
4. `f5` is copied and run 6 times, each with a list of 5 nodes as input to f5.run method.

### type
#### Purpose and Behavior
- Currently, only matters if it is set as "node"
- Format: `{'x':{'type': 'node' or anything else}}`
- If type is "node":
  - Previous Step's nodes (a special dict) will be used as the input
- If type is not "node":
  - By default, the 'content' value of the nodes will be used. If "field" is defined in input_schema, the value corresponding to the field will be used

#### Example Node Structure
```python
s.p6.sub_node_graph.nodes[1026]
Out: 
{'node_id': uuid_ex(1026),
 'content': 10,
 'type': str,
 'name': 'input',
 'level': 0,
 'step_name': 'p6;InputInitializer:sp0',
 'step_id': 0,
 'extra': {'x': 15},
 'parent_ids': [],
 'if_output': True,
 'cp_name': 'p6;InputInitializer'}
```

#### Behavior based on step_type
- If type is "node" and step_type is "node_to_node":
  - Each of the above nodes will be used as an input for the next Component
- If type is not "node":
  - By default, the content (10 in this example) will be used as the input for the next Component
  - if "field" is "step_id" for example, 0 will be used.

### field
#### Purpose and Behavior
- The input of a Component.run can be nodes (a special dict) or anything inside the nodes
- For example (check Example Node Structure of the previous section), Component.input_schema= {"y": {"type": str, "field": "extra.x"}}
  - First, get all the nodes(dict) from the previous Step, you have a list of nodes.
  - As the type is not "node", 15 (from 'extra.x') will be used as the input for the next Component

### filter_cri
#### Purpose and Behavior
- Uses MongoDB query language with some extensions
- By default, all nodes from the previous one step will be processed
- If defined, the specified filter_cri will be used instead as the filtering criteria of nodes.

#### Example
```python
filter_cri={"step_name": {"$regex": "f6", "$order": -1}}
```
- This means:
  - $regex:"f6" means that step_name should contain "f6". 
  - $order:-1 means that
    - If many nodes confirm with this criteria, they will be grouped by step_name as list of list of nodes
    - The last list of nodes will be selected, as their order is -1

## cache_schema
### Purpose and Behavior

The Cache Schema is a mechanism used in Pipelines and their sub-Components and Steps to manage shared caching of values. It provides a flexible way to store, retrieve, and initialize cached values across different parts of the pipeline.

- The cache is shared across the pipeline, allowing for efficient data sharing between components.

### Structure and Example

The cache schema is defined as a dictionary:

```python
cache_schema = {
    "z": {
        "key": "[cp_or_pp.name]",
        "initializer": lambda: z(),
    },
    "<SELF>": {"key": "haha"},
    "a": {"key": "<TEMP>", "initializer": "[node_graph]"}
}
```

### Key Components

1. **param_name**: The name of the parameter in the component (e.g., "z", "<SELF>", "a").
2. **key**: Specifies the cache key stored in cache.
3. **initializer**: A function or expression to initialize the value if not found in cache.

### Special param_name

- **`<SELF>`**: A special parameter that refers to the component itself.

### Special Keys and Behaviors

1. **Anything enclosed in []**: A dynamic key that uses the name of the current component or pipeline. 
   (e.g., `"[cp_or_pp.name]"` means the key stored in cache is `self.cp_or_pp.name`)
2. **`<TEMP>`**: Indicates a temporary value that should be reinitialized each time and not stored in cache.
   - Use `<TEMP>` for values that should not persist in the cache between runs.

### Caching Process

1. For each parameter in the cache schema:
   - Generate the cache key using the specified "key" (e.g., k).
   - Check if the value exists in the cache.
   - If not found, use the initializer to create the value.
   - Store the value in the cache (except for `<TEMP>` keys). (e.g., cache = {k:v})
   - Update the parameter with the cached or initialized value.

2. Special handling for `<SELF>`:
   - If found in cache, use it directly as the current component in `self.cp_run_func`.

### Initializer Types

1. **Callable**: A function that can accept arguments based on available parameters and cache values.
2. **String Expression**: Enclosed in square brackets, refers to an attribute path in the current object.

### Explanation of the Example

1. Parameter "z":
   - `"key": "[cp_or_pp.name]"`: Cache key is dynamically generated using the current component or pipeline name.
   - `"initializer": lambda: z()`: If not in cache, initialized by calling `z()`.

2. Parameter "<SELF>":
   - Refers to the component itself.
   - `"key": "haha"`: Cache key for storing the entire component instance.
   - No initializer provided as it refers to the existing component instance.

3. Parameter "a":
   - `"key": "<TEMP>"`: Recomputed each time, not stored in persistent cache.
   - `"initializer": "[node_graph]"`: Initial value obtained by evaluating `self.node_graph`.

Resulting cache:
```python
cache = {self.cp_or_pp.name: z(), "haha": self}  # <TEMP> is ignored
```


## output_schema
### Purpose and Behavior
- The 'type' and 'name' attributes will be passed into the nodes the Step created

## output_format

As mentioned previously, when Step.run, Components will be cloned and the result of Component.run will be stored in Pipeline.sub_node_graph(and Step.node_graph). The `output_format` variable determines how the result of a Component.run is processed and added to the node graph. It supports several formats:

### 1. "node_like" or "node"
- The output of the Component should be a node-like dict.
- New nodes are created based on the output dict of the Component, especially "content" and "extra" attributes of the dict.
- if the output nodes of the Component contains "parent_nodes" attributes, then it will be used to identify parent nodes.

### 2. "graph"
- Expects the result to be a networkx graph.
- Adds missing information (step_id, step_name, cp_name) to nodes in the result graph.
- Combines the result graph with the existing node graph.
- Identifies newly added nodes and appends them to `new_nodes`.

### 3. "dict"
- For each key-value pair in the result:
  - Creates a new node with the value as content.
  - if output is {x:y, a:b}, then 2 nodes will be created with node's name x and a respectively

### 4. "none"
- Does not process the result or add any nodes.

### 5. Default (if not "node")
- Creates a new node with the entire result as content.


## Bindings and Linkings

### Overview

Bindings and linkings determine the execution order of Components within a Pipeline.

### Bindings

Bindings define conditions for Component execution after a Step completes.

#### Key Concepts:

1. After each Step, the Pipeline checks if Components should be triggered based on their bindings.
2. Components use `if_trigger_bindings` to determine execution.
3. If bindings are satisfied, a new Step is created and added to the Pipeline's priority queue.

### Linkings

Linkings define direct connections between Components for specific execution order.

#### Key Concepts:

1. Linkings create direct relationships between Components.
2. After a Step completes, the Pipeline checks linkings to determine the next Component to execute.
3. The previous Component checks which other Components it can link to.


### Example

```python
s = Session()
s.f4, s.f6, s.f5 = f4(), f6(), f5()
s.p6 = s.f4 | s.f6 | s.f5

[c.full_name for c in s.p6.contains]
# ['p6;InputInitializer', 'p6;f4.0', 'p6;f6.0', 'p6;f5.0']

[c.uuid for c in s.p6.contains]
# [uuid_ex(1057), uuid_ex(1064), uuid_ex(1069), uuid_ex(1074)]

[c.bindings for c in s.p6.contains]
# [
#   [],
#   [{'cp_or_pp.uuid': {'$eq': uuid_ex(1057)}}],
#   [{'cp_or_pp.uuid': {'$eq': uuid_ex(1064)}}],
#   [{'cp_or_pp.uuid': {'$eq': uuid_ex(1069)}}]
# ]
```

This example demonstrates how Components are linked and their bindings are set up in a Pipeline.

### Execution Process

The Pipeline's `run` method manages Step execution:

1. Execute the next Step from the priority queue (Pipeline.sub_steps_q).
2. Check linkings to determine the next Component.
3. Check all Components' bindings for potential triggering.
4. Create new Steps for Components with satisfied bindings.

This process ensures correct execution order based on linkings and bindings.


