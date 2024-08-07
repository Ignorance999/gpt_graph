# Tutorial 1: Basics

This tutorial demonstrates how to build Pipelines using the GPT Graph library. We'll cover component creation, session management, pipeline construction, and graph analysis.

*Note: You can refer to `test/test_pipeline.py -> test_1_simple_pipeline_execution()`*

## Defining Components

First, let's define our components. We'll use a helper class and three functions:

```python
class z:
    def __init__(self):
        self.z = 0

    def run(self):
        self.z += 1
        return self.z

@component(
    step_type="node_to_list",
    cache_schema={
        "z": {
            "key": "[cp_or_pp.name]",
            "initializer": lambda: z(),
        }
    },
)
def f4(x, z, y=1):
    return x + y + z.run(), x - y + z.run()

@component(step_type="list_to_node")
def f5(x):
    return np.sum(x)

@component(
    step_type="node_to_list",
    cache_schema={"z": {"key": "[base_name]", "initializer": lambda: z()}},
)
def f6(x, z):
    return [x, x - z.run(), x - z.run()]
```

These components demonstrate various features:
- Caching with `cache_schema`
- Different step types: "node_to_list" and "list_to_node"

### Key points:

1. **Component Definition with Decorator**
   - When using the `@component` decorator to define a Component:
     - `self.input_schema` is automatically defined if not specified
     - `self.input_schema` for a Component follows this structure:
       ```
       {y: {dim: 0, 1...,
            group: g,
            filter_cri: {}}}
       ```

2. **Step Types**
   - "node_to_list" or "node_to_node":
     - Previous Step creates a list of nodes (dict), for current Step, the Component.run function will be processed x times (x is the number of nodes)
     - `dim` for that parameter is larger than -1
   - "list_to_node" or "list_to_list":
     - The entire list of nodes will be used as the input of the current Step
     - `dim` for that parameter is -1

3. **Cache Schema**
   - Cache can be stored and preserved across Steps
   - Prevents reinitiation of the same object for later nodes
   - `[]` in cache_schema indicates:
     - Cache is a dict, its key is determined by the "key"'s value in cache_schema
     - `[xx]` means that the key stored in cache will be the value of `getattr(Step, xx)`
     - Example after running:
       ```python
       s.p6.cache
       # Output: {'f4.0': <__main__.z at 0x2b93593b340>, 'f6': <__main__.z at 0x2b9359461c0>}
       ```
     - (You can refer to the following example)
       For f4 cache_schema, `"key": "[cp_or_pp.name]"`,
       `s.p6.contains[1].steps[0].cp_or_pp.name == 'f4.0'`
       s is Session
       s.p6 is a Pipeline
       s.contains[1] is a Component, its steps[0] is a Step
       [cp_or_pp.name] in cache_schema is applied to self(which is Component f4.0's Step)


## Creating a Session and Pipeline

Now, let's create a session and build our pipeline:

```python
s = Session()
s.f4 = f4()
s.f6 = f6()
s.f5 = f5()
s.p6 = s.f4 | s.f6 | s.f5
```

This creates a pipeline `p6` that chains components `f4`, `f6`, and `f5` together.


## Running the Pipeline

We can run the pipeline with an input:

```python
result = s.p6.run(input_data=10)
```

## Analyzing the Pipeline Execution

Let's break down what happens during execution:

```
Step: p6;InputInitializer:sp0
text = 10 (2 characters)

Step: p6;f4.0:sp0
text = 12 (2 characters)
text = 11 (2 characters)

Step: p6;f6.0:sp0
text = 12 (2 characters)
text = 11 (2 characters)
text = 10 (2 characters)
text = 11 (2 characters)
text = 8 (1 characters)
text = 7 (1 characters)

Step: p6;f5.0:sp0
text = 59 (2 characters)
```

This output shows the progression of data through each step of the pipeline.

Before any analysis, let's check the final cache produced:

```python
s.p6.cache
{
    'f4.0': <__main__.z at 0x280d292f0d0>,
    'f6': <__main__.z at 0x280d2981c70>
}
```

### Initial Step: p6;InputInitializer:sp0
The initial value is set to 10.

### Step: p6;f4.0:sp0
Function f4 is applied:

```python
def f4(x, z, y=1):
    return x + y + z.run(), x - y + z.run()
```

- Initial x = 10
- y = 1 (default value)
- z.run() returns 1 on first call, 2 on second call

First output: 10 + 1 + 1 = 12
Second output: 10 - 1 + 2 = 11

### Step: p6;f6.0:sp0
Function f6 is applied to each output from f4:

```python
def f6(x, z):
    return [x, x - z.run(), x - z.run()]
```

For x = 12:
- First element: 12
- Second element: 12 - 1 = 11 (z.run() returns 1)
- Third element: 12 - 2 = 10 (z.run() returns 2)

For x = 11:
- First element: 11
- Second element: 11 - 3 = 8 (z.run() returns 3)
- Third element: 11 - 4 = 7 (z.run() returns 4)

### Step: p6;f5.0:sp0
Function f5 is applied to all the outputs from f6:

```python
def f5(x):
    return np.sum(x)
```

The sum of all outputs is: 12 + 11 + 10 + 11 + 8 + 7 = 59

## Examining the Pipeline Structure

We can inspect the pipeline's structure:

```python
s.p6.contains
[
    <InputInitializer(
        full_name=p6;InputInitializer, 
        base_name=InputInitializer, 
        name=InputInitializer, 
        uuid=1580
    )>,
    <DerivedComponent(
        full_name=p6;f4.0, 
        base_name=f4, 
        name=f4.0, 
        uuid=1587
    )>,
    <DerivedComponent(
        full_name=p6;f6.0, 
        base_name=f6, 
        name=f6.0, 
        uuid=1592
    )>,
    <DerivedComponent(
        full_name=p6;f5.0, 
        base_name=f5, 
        name=f5.0, 
        uuid=1597
    )>
]
```

```python
type(s.p6)  # Output: gpt_graph.core.pipeline.Pipeline
s.p6.sub_node_graph.nodes  # Shows all nodes in the pipeline
```

To get a more detailed view of the nodes:

```python
s.p6.sub_node_graph.show_nodes_by_attr("step_name")
```

Output:

```
p6;InputInitializer:sp0: {'ids': [uuid_ex(1604)], 'type': <class 'str'>}
p6;f4.0:sp0: {'ids': [uuid_ex(1606), uuid_ex(1607)], 'type': typing.Any}
p6;f6.0:sp0: {'ids': [uuid_ex(1609), uuid_ex(1610), uuid_ex(1611), uuid_ex(1612), uuid_ex(1613), uuid_ex(1614)], 'type': typing.Any}
p6;f5.0:sp0: {'ids': [uuid_ex(1616)], 'type': typing.Any}
```

## Inspecting Individual Nodes

We can look at specific nodes for more details:

```python
s.p6.sub_node_graph.nodes[1604]
```

This shows us the input node:

```python
{
 'node_id': uuid_ex(1604),
 'content': 10,
 'type': str,
 'name': 'input',
 'level': 0,
 'step_name': 'p6;InputInitializer:sp0',
 'step_id': 0,
 'extra': {},
 'parent_ids': [],
 'if_output': True,
 'cp_name': 'p6;InputInitializer'
}
```

And we can look at output nodes, like the one from `f4`:

```python
s.p6.sub_node_graph.nodes[1606]
```

Output:

```python
{
 'node_id': uuid_ex(1606),
 'content': 12,
 'type': typing.Any,
 'name': 'output',
 'level': 1,
 'step_name': 'p6;f4.0:sp0',
 'step_id': 1,
 'extra': {},
 'parent_ids': [uuid_ex(1604)],
 'if_output': True,
 'cp_name': 'p6;f4.0'
}
```

## sub_steps_history

After a Step finished running, it will be put into sub_steps_history:

```python
s.p6.sub_steps_history
[
    <Step(
        full_name=p6;InputInitializer:sp0, 
        name=InputInitializer:sp0, 
        uuid=1598
    )>,
    <Step(
        full_name=p6;f4.0:sp0, 
        name=f4.0:sp0, 
        uuid=1605
    )>,
    <Step(
        full_name=p6;f6.0:sp0, 
        name=f6.0:sp0, 
        uuid=1608
    )>,
    <Step(
        full_name=p6;f5.0:sp0, 
        name=f5.0:sp0, 
        uuid=1615
    )>
]
```
