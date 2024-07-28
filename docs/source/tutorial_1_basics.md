# tutorial 1 Basics

This tutorial demonstrates how to build and analyze complex pipelines using the GPT Graph library. We'll cover component creation, session management, pipeline construction, and graph analysis.

Note: you can refer to test/test_pipeline.py -> test_1_simple_pipeline_execution()

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

Key points:

1. Component Definition with Decorator
   - When using the @component decorator to define a Component:
     - `self.input_schema` is automatically defined for `Component.__init__`
     - This occurs if `if_auto_detect_input=True`

2. Input Schema Format
   - `self.input_schema` for a Component follows this structure:
     ```
     {y: {dim: 0, 1...,
          group: g,
          filter_cri: {}}}
     ```

3. Step Types
   - "node_to_list" or "node_to_node":
     - Function acts on individual nodes
     - `dim` is non-negative (starts from 0)
   - "list_to_node" or "list_to_list":
     - Function acts on lists
     - `dim` is -1

4. Examples of Step Types
   - f4: 
     - Single input x, outputs 2 items
     - Step type: "node_to_list"
   - Similar logic applies to f5 and f6

5. Cache Schema
   - Purpose: Optimize batch processing of nodes
   - Prevents reinitiation of the same object for later nodes
   - Uses previously defined cache instead

6. Special Indicator in Cache Schema
   - `[]` in cache_schema indicates:
     - The key stored in the cache will be named as current `Step.[xx]`
     - Note: Step is produced by Component to handle the actual running routine
     - e.g. for this example after running,
     ```python
     s.p6.cache
     Out[4]: {'f4.0': <__main__.z at 0x2b93593b340>, 'f6': <__main__.z at 0x2b9359461c0>}

     ```

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

Before any analysis, let's check the final cache produced. We see that both z in f4 and f6 are cached at different placed.
If you remember in f6.cache_schema, z's key is [base_name], here because of this [] operator, the actual key is s.p6.contains\[2\].steps\[0\].base_name, which is 'f6'
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
   Function f4 is applied. Let's see how it works:

   ```python
   def f4(x, z, y=1):
       return x + y + z.run(), x - y + z.run()
   ```

   - Initial x = 10
   - y = 1 (default value)
   - z.run() returns 1 on first call, 2 on second call (due to the increment in the z class in cache)

   First output: 10 + 1 + 1 = 12
   Second output: 10 - 1 + 2 = 11

   This explains why we see:
   text = 12 (2 characters)
   text = 11 (2 characters)
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

   This explains the output:
   text = 12 (2 characters)
   text = 11 (2 characters)
   text = 10 (2 characters)
   text = 11 (2 characters)
   text = 8 (1 characters)
   text = 7 (1 characters)

### Step: p6;f5.0:sp0
   Function f5 is applied to all the outputs from f6:

   ```python
   def f5(x):
       return np.sum(x)
   ```

   The sum of all outputs is: 12 + 11 + 10 + 11 + 8 + 7 = 59

   This explains the final output:
   text = 59 (2 characters)

The logic flows as follows:
1. Start with 10
2. Apply f4 to get two outputs: 12 and 11
3. Apply f6 to each of these outputs, resulting in 6 values: 12, 11, 10, 11, 8, 7
4. Finally, apply f5 to sum all these values, resulting in 59

The z class acts as a counter that increments each time it's called, which affects the calculations in f4 and f6. This stateful behavior contributes to the changing results as the pipeline progresses.


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
So, s as a Session, you have defined p6 in it. p6 contains 4 components, 3 of them are defined by us, the first one is the default one handling inputs.


```python
type(s.p6)  # Output: gpt_graph.core.pipeline.Pipeline
s.p6.sub_node_graph.nodes  # Shows all nodes in the pipeline
```
sub_node_graph is a Graph object that contains all nodes in the pipeline.
sub_steps are created by Component contained in the Pipeline. After they are created, they are added into Pipeline.sub_steps_q.
sub_steps_q is a priority queue that will pop a Step each time in the while loop for running.
after running the Step.run, will check if_trigger_bindings/if_trigger_linkings, if any Componenet satisfy the criteria, they will create a sub-step and put into the sub_steps_q.
When you run a pipeline using s.p6.run(), the following things will occur: 
```python
"""
Under Pipeline.run
"""
print(f"running: {self.name}")

self.load_params(params_file=params_file)  # using Closure method
params["self"] = self
self.set_params(params)

for cp in self.contains:
    if not cp.params_check():
        raise

# initialize steps
self.sub_steps = {}  # all created steps
self.sub_steps_q.initialize()
self.sub_steps_history = []
self.sub_node_graph.initialize()
self.sub_step_graph.initialize()

# cp_roots are just InputInitializer set in __init__
for cp in self.cp_roots:
    self.create_sub_step(
        cp=cp,
        if_ult_input=True,
        priority=0,
        parent_step_names=[],
    )

# Execute each step in the steps q
self.curr_step_id = 0
while self.sub_steps_q:
    _, step = self.sub_steps_q.pop()
...
    # Check for new steps created by linkings
    previous_step = self.sub_steps_history[-1]
    prev_cp = previous_step.cp_or_pp
    for cp in self.contains:
        if prev_cp.if_trigger_linkings(next_cp=cp):
            self.route_to(step_name=cp.full_name)

    # Check for new steps created by bindings
    for component in self.contains:
        if component.if_trigger_bindings(previous_step=previous_step):
            new_step = self.create_sub_step(
                cp=component,
                params={},
                priority=0,
                parent_step_names=[previous_step.full_name],
            )


```

To get a more detailed view of the nodes:
```python
s.p6.sub_node_graph.show_nodes_by_attr("step_name")
```

This gives us:

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

Which gives us:

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
After a Step finished running, it will be put into sub_steps_history.
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



## Conclusion
1. Component creation with custom caching and step types
2. Easy pipeline construction using the `|` operator
3. Detailed execution tracing
4. In-depth analysis of pipeline structure and individual nodes


