# GPT Graph project structure

## Core Concepts
### Shorthand Notations
- Pipeline: pp
- Component: cp

### Closure
The Closure class serves as the base class for both Component and Session classes in our system. Its primary purpose is to establish and manage hierarchical relationships between different elements of our pipeline.

Key features of the Closure class:

1. **Closure.contains**: This is a list that forms the backbone of the relationship structure. It holds references to other Components, Pipelines that are contained within the current instance.

2. **Hierarchical Structure**: 
   - A Session can contain other Components or Pipelines.
   - A Pipeline can contain other Pipelines and Components.

#### Concept of Names in the Component Hierarchy

In our system, different types of names are used to identify and reference components within a hierarchical structure. Let's break this down:

1. **Name Types**:
   - `full_name`: The complete path of the component in the hierarchy.
   - `base_name`: The original name of the component.
   - `name`: The component's name, potentially with an index if it's contained in other Pipelines.

2. **Naming Convention**:
   - Components/Pipelines contained within other Pipelines are assigned an index (lid).
   - For example, `f4` might become `f4.0` or `f4.1` if there are multiple instances.

3. **Hierarchy Representation**:
   - The `full_name` uses semicolons (`;`) to represent the containment hierarchy.
   - Example: `p3;p6.0` means this is the first instance of `p6` within `p3`.

4. **Example Hierarchy**:

```python
s3 = Session()
s3.f4 = f4()
s3.f6 = f6()
s3.f5 = f5()
g = Group(
    filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
    parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
)
s3.p6 = s3.f4 | s3.f6 | s3.f5.prepend(g)
s3.p3 = s3.p6 | s3.p6

# Printing information for s3
print("s3 full_name:", s3.full_name)
print("s3 base_name:", s3.base_name)
print("s3 name:", s3.name)

# Printing information for s3.p6
print("s3.p6 full_name:", s3.p6.full_name)
print("s3.p6 base_name:", s3.p6.base_name)
print("s3.p6 name:", s3.p6.name)

# Printing information for s3.p6.contains[1]
print("s3.p6.contains[1] full_name:", s3.p6.contains[1].full_name)
print("s3.p6.contains[1] base_name:", s3.p6.contains[1].base_name)
print("s3.p6.contains[1] name:", s3.p6.contains[1].name)

# Printing information for s3.p3
print("s3.p3 full_name:", s3.p3.full_name)
print("s3.p3 base_name:", s3.p3.base_name)
print("s3.p3 name:", s3.p3.name)

# Printing information for s3.p3.contains[1]
print("s3.p3.contains[1] full_name:", s3.p3.contains[1].full_name)
print("s3.p3.contains[1] base_name:", s3.p3.contains[1].base_name)
print("s3.p3.contains[1] name:", s3.p3.contains[1].name)

""" output:
s3 full_name: Session
s3 base_name: Session
s3 name: Session

s3.p6 full_name: p6
s3.p6 base_name: p6
s3.p6 name: p6

s3.p6.contains[1] full_name: p6;f4.0
s3.p6.contains[1] base_name: f4
s3.p6.contains[1] name: f4.0

s3.p3 full_name: p3
s3.p3 base_name: p3
s3.p3 name: p3

s3.p3.contains[1] full_name: p3;p6.0
s3.p3.contains[1] base_name: p6
s3.p3.contains[1] name: p6.0
"""
```

5. **Naming Examples**:

   | Component       | full_name | base_name | name  |
   |-----------------|-----------|-----------|-------|
   | s3              | Session   | Session   | Session | (default value without it being assigned to other Session)
   | s3.p6           | p6        | p6        | p6    |
   | s3.p6.contains[1] | p6;f4.0   | f4        | f4.0  |
   | s3.p3           | p3        | p3        | p3    |
   | s3.p3.contains[1] | p3;p6.0   | p6        | p6.0  |

6. **Parameter Setting Methods**:
   - `Closure.set_placeholders()`: Set parameters as placeholders for later replacement.
   - `Closure.load_params()`: Load parameters from a TOML configuration file.
   - `Closure.set_params()`: Manually set parameters.

7. **Parameter Setting Syntax**:
   - In `set_params()`, use `;` for containment relationship and `:` for parameter key.
   - Example: `{'p;c:param_key': param_value}` sets `param_key` of component `c` within pipeline `p`.

8. **Example of Manual Parameter Setting**:
   ```python
   self.set_params({"youtube_lister;entry_ids": entry_list})
   ```

For more detailed examples and usage, refer to the `tutorial_6_read_book` documentation.


### Component

Components are the building blocks of our pipeline system. There are three ways to create a Component:

1. **Class-based Component** (category: "class" or "static")
   Inherit from the `Component` class in `gpt_graph.core.component`:

   ```python
   class CustomComponent(Component):
       step_type = "node_to_list"
       input_schema = {"source_url": {"type": str}}
       cache_schema = {}
       output_schema = {"video_data": {"type": "list"}}
       output_format = "node_like"
   ```

2. **Decorator-based Static Component** (category: "static")
   Use the `@component` decorator from `gpt_graph.decorators.component`:

   ```python
   @component(step_type="list_to_node")
   def f5(x):
       return np.sum(x)
   ```

3. **Method-based Component** (category: "method")
   Define the component as a method inside a Pipeline class, still using the `@component` decorator.

#### Component Categories

The `Component.category` determines how the function will be executed when wrapped inside a Step:

- **"class"**: The Step initiates the component as a class and calls `cp.run()`.
- **"static"**: The Step directly calls the static function inside the Component.
- **"method"**: The Step plugs in `self` as the current running Pipeline, so the method runs as if bound to the Pipeline.

#### Pipeline Execution

When `Pipeline.run()` is called:
1. Components in the pipeline are checked against their criteria (bindings) or the last running step's criteria (linkings).
2. If criteria are met, Steps are created.
3. Steps run according to their priorities, adding nodes to `pp.sub_node_graph` (a wrapper of a networkx graph).

#### Input Schema

The input schema defines how input data is processed. For example:

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

Key concepts:
- **dim**: Determines how input nodes are processed.
  - `-1`: All nodes from the previous step are input as a list.
  - `≥0`: The component runs multiple times, once for each node.

- **Matching dimensions**: When multiple inputs have the same dimension, they should have the same number of elements.

Example:
```python
input_schema = {"y": {"dim": 1}, "x": {"dim": 1}}
```
If `f(x,y) = x+y`, and `x = [1,2]`, `y = [1,1,2,2]`, the Step generates four copies of `f`:
```
f(1,1), f(1,1), f(2,2), f(2,2)
```

##### Groups

Groups, created by `Group()`, are used to plug values into function parameters:

```python
g = Group(
    filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
    parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
)
s.p6 = s.f4 | s.f6 | s.f5.prepend(g)
```

In this example:
1. `g` is prepended to Component `s.f5` in Pipeline `s.p6`.
2. When `s.p6.run()` is called, after `p6;f4.0`, `p6;f5.0` calls `g`.
3. `g` returns a list of lists of nodes (e.g., 6 lists of 5 nodes each).
4. `f5` is copied and run 6 times, each with a list of 5 nodes as input.

This flexible structure allows for complex data processing pipelines with dynamic input handling and grouping.


##### Type
###### Purpose and Behavior
- Only matters if it is set as "node" or not
- Format: `{'x':{'type': 'node' or anything else}}`
- If type is "node":
  - Previous Step's nodes (a special dict) will be used as the input
- If type is not "node":
  - The 'content' value of the nodes will be used

###### Example Node Structure
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

###### Behavior based on step_type
- If type is "node" and step_type is "node_to_node":
  - Each of the above nodes will be used as an input for the next Component
- If type is not "node":
  - The content (10 in this example) will be used as the input for the next Component

##### Field
###### Purpose and Behavior
- The input of a Component.run can be nodes (a special dict) or anything inside the nodes
- Example usage: `{"field": "extra.x"}`
  - This will filter all nodes of previous Steps
  - If type is not "node", 15 (from 'extra.x') will be used as the input for the next Component

##### Filter Criteria
###### Purpose and Behavior
- Uses MongoDB query language with some extensions
- By default, all nodes from the previous step will be processed
- If defined, the specified filter_cri will be used instead

###### Example
```python
filter_cri={"step_name": {"$regex": "f6", "$order": -1}}
```
- This means:
  - step_name should contain "f6"
  - If many nodes confirm this criteria, they will be grouped by step_name
  - The last group will be selected

#### Cache Schema
##### Purpose and Behavior
- Cache is an attribute belonging to Pipelines and all its sub-Components and Steps
- They share the same self.cache

##### Example
```python
cache_schema={
    "z": {
        "key": "[cp_or_pp.name]",
        "initializer": lambda: z(),
    }
}
```

##### Key Details
- `[cp_or_pp.name]` is a special operator
- What's stored in cache: `self.cache[getattr(getattr(self, "cp_or_pp"), "name"]`
- If this key-value pair exists, its value will be used as z in the Component.run
- If not found, it will be initiated using the initializer

#### Output Schema
##### Purpose and Behavior
- The 'type' and 'name' attributes will be passed into the nodes the Step created

#### Output Format

The `output_format` variable determines how the result of a Component is processed and added to the node graph. It supports several formats:

##### 1. "node_like" or "node"
- The output of the Component should be a node-like dict.
- New nodes are created based on the output dict of the Component, especially "content" and "extra" attributes of the dict.

##### 2. "graph"
- Expects the result to be a graph structure.
- Adds missing information (step_id, step_name, cp_name) to nodes in the result graph.
- Combines the result graph with the existing node graph.
- Identifies newly added nodes and appends them to `new_nodes`.

##### 3. "dict"
- Treats the result as a dictionary.
- For each key-value pair in the result:
  - Creates a new node with the value as content.
  - Uses the key to match and apply relevant output_info.

##### 4. "none"
- Does not process the result or add any nodes.

##### 5. Default (if not "node")
- Creates a new node with the entire result as content.
- Applies all output_info to the node.

#### Bindings

Bindings determine the execution order of Components within a Pipeline:

- When Pipeline.run is executed, after each Step is run, different Components (cp) contained in the Pipeline (pp) will be asked Component.if_trigger_bindings.
- If it returns True, this Component will create a Step and put it into Pipeline.sub_steps_q (a priority queue).
- When using the | operator to link Components together, cp.bindings will be filled in automatically.

Example:
```python
s = Session()
s.f4 = f4()
s.f6 = f6()
s.f5 = f5()
s.p6 = s.f4 | s.f6 | s.f5

[c.full_name for c in s.p6.contains]
Out[11]: ['p6;InputInitializer', 'p6;f4.0', 'p6;f6.0', 'p6;f5.0']

[c.uuid for c in s.p6.contains]
Out[10]: [uuid_ex(1057), uuid_ex(1064), uuid_ex(1069), uuid_ex(1074)]

[c.bindings for c in s.p6.contains]
Out[9]: 
[[],
 [{'cp_or_pp.uuid': {'$eq': uuid_ex(1057)}}],
 [{'cp_or_pp.uuid': {'$eq': uuid_ex(1064)}}],
 [{'cp_or_pp.uuid': {'$eq': uuid_ex(1069)}}]]
```

In this example:
- After running p6;f4.0's Step, all the Components will test bindings again.
- Because the previous Step.cp_or_pp.uuid == 1064, p6;f6.0 satisfies its own bindings and will be run next.

### Pipeline
- Inherited from Component, which is inherited from Closure
- When you connect components like `p | c1 | c2`, the `Pipeline.connect` method is called.
- To understand more about `Pipeline.run`, refer to the tutorials.

### Step
Steps are executable units within a pipeline.
- They are stored in `Pipeline.sub_steps` / `sub_steps_q` during runtime.
- After execution, they are moved to `sub_steps_history`.

#### Priority
- Uses a priority queue.
- Within `sub_steps_q`, Steps with higher priority will be run first.
- You can also check `sub_step_graph`, which is a StepGraph object.
- Priority levels:
  - 0: default
  - 1: route_to

### Graph
Graphs represent the structure of connected components and steps.
- Graph is a wrapper of networkx graph.
- `Graph.graph` is a networkx DiGraph.

#### Important methods
- `add_node`
- `filter_nodes`

## Parameter Handling

### Parameter Priority
Parameters can have different priorities:

| Priority | Description |
|----------|-------------|
| 0        | Default |
| 1+       | Loading from config file|
| 1000+    | Manually set params |
| ...      | ... |

### Parameter Types
Parameters have several attributes:

1. **Type**: 
   - input
   - param
   - placeholder

2. **Status**: 
   - input
   - empty
   - default
   - assigned
   - ult_input
   - config
   - filter_cri
   - cache

3. **Value**: 
   - The actual parameter value
   - `<CACHE>`
   - `<INPUT>`
   - `<EMPTY>`

4. **priority**: 
   - 1000+ indicates a manual change, rather than a config file change or default value

5. **placeholder**: 
   - Represented as `[some thing]`


