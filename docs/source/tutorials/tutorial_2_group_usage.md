# tutorial 2 using Group

This documentation explains the setup of a session with multiple components and a pipeline, focusing on the behavior of the group 

Note: you can refer to test/test_pipeline.py -> test_2_pipeline_with_group()

## Session Initialization
```python
s = Session()
s.f4 = f4()
s.f6 = f6()
s.f5 = f5()
```

Here, we create a new Session and add three components: `f4`, `f6`, and `f5`. The components' definition are the same as tutorial 1

## Group Definition

```python
g = Group(
    filter_cri={"step_name": {"$regex": "f6", "$order": -1}},
    parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}},
)
```

A Group is created with specific filtering criteria:
- `filter_cri`: Selects nodes with step names matching the regex "f6", ordered in descending order.
- `parent_filter_cri`: Selects parent nodes with step names matching the regex "f4", ordered in descending order.
- Also notice that, the nodes will group by parent_filter_cri's value. The output is a list of list of nodes.
- filter_cri and parent_filter_cri inheritly are using Graph.filter_nodes method, which is using mql (mongodb query language), with some twist, like $order or $lambda. {"step_name": {$order:-1}} means that all the nodes will sort by step_name, and then select the latest nodes with the same step_name.

## Pipeline Creation

```python
s.p6 = s.f4 | s.f6 | s.f5.prepend(g)
# you can also use the following. They have same effect
# s.p6 = s.f4 | s.f6 | s.f5.update_input_schema({"x": {"group": g}})
```

A pipeline `p6` is created by chaining `f4`, `f6`, and `f5`. The group `g` is prepended to `f5`.
prepend a Group, means that s.f5.input_schema will be updated by {"x": {"group": g}} on top of original value.

## Pipeline Execution

```python
result = s.p6.run(input_data=10)
```

The pipeline is executed with an input of 10.

Certainly. I'll update the documentation to explain why the result looks like this, step by step. Here's the revised section of the documentation:

## Output Analysis and Explanation

the output is
```
Step: p6;InputInitializer:sp0
Removed 0 nodes matching the attribute dictionary.
	text = 10 (2 characters)
	text = <Step(full_name=p6;f... (57 characters)

Step: p6;f4.0:sp0
Removed 0 nodes matching the attribute dictionary.
	text = 12 (2 characters)
	text = 11 (2 characters)
	text = <Step(full_name=p6;f... (57 characters)

Step: p6;f6.0:sp0
Removed 0 nodes matching the attribute dictionary.
	text = 12 (2 characters)
	text = 11 (2 characters)
	text = 10 (2 characters)
	text = 11 (2 characters)
	text = 8 (1 characters)
	text = 7 (1 characters)
	text = <Step(full_name=p6;f... (57 characters)

Step: p6;f5.0:sp0
Removed 0 nodes matching the attribute dictionary.
	text = 33 (2 characters)
	text = 26 (2 characters)
```

### Step: p6;f4.0:sp0

```
Removed 0 nodes matching the attribute dictionary.
text = 12 (2 characters)
text = 11 (2 characters)
text = <Step(full_name=p6;f... (57 characters)
```

- Function f4 is applied: `def f4(x, z, y=1): return x + y + z.run(), x - y + z.run()`
- With x = 10, y = 1, and z.run() returning 1 and 2 for successive calls:
  - First output: 10 + 1 + 1 = 12
  - Second output: 10 - 1 + 2 = 11
- No nodes are removed as this step matches the parent_filter_cri in the Group.

### Step: p6;f6.0:sp0

```
Removed 0 nodes matching the attribute dictionary.
text = 12 (2 characters)
text = 11 (2 characters)
text = 10 (2 characters)
text = 11 (2 characters)
text = 8 (1 characters)
text = 7 (1 characters)
text = <Step(full_name=p6;f... (57 characters)
```

- Function f6 is applied: `def f6(x, z): return [x, x - z.run(), x - z.run()]`
- Applied to each output from f4:
  - For x = 12: [12, 12-1, 12-2] = [12, 11, 10]
  - For x = 11: [11, 11-3, 11-4] = [11, 8, 7]
- No nodes are removed as this step matches the filter_cri in the Group.

### Step: p6;f5.0:sp0

```
Removed 0 nodes matching the attribute dictionary.
text = 33 (2 characters)
text = 26 (2 characters)
```

- Function f5 is applied: `def f5(x): return np.sum(x)`
- The Group (g) is prepended to f5,.
- The Group `g` is defined with:
   - `filter_cri={"step_name": {"$regex": "f6", "$order": -1}}`
   - `parent_filter_cri={"step_name": {"$regex": "f4", "$order": -1}}`
first filter f6, results are 6 nodes -> 12,11,10,11,8,7
second filter f4, results are 2 nodes -> 12, 11
12 -> 12,11,10 and 11->11,8,7; -> means the linkings relationship between parent and child nodes, as f4 | f6
Therefore, g is a list of Group, first contains 3 nodes 12,11,10; second contains 3 nodes 11,8,7
```python
s.p6.contains[-1].input_schema["x"]["group"].contains
[<gpt_graph.core.group.Group at 0x280d29940a0>,
 <gpt_graph.core.group.Group at 0x280d29990a0>]
```
- f5 sums the outputs from f6 in two groups:
  - Sum of [12, 11, 10] = 33
  - Sum of [11, 8, 7] = 26






