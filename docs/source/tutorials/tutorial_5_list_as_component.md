# tutorial 5 List as Component

Note: you can refer to test/test_pipeline.py -> test_6_complex_pipeline_with_input_initializers()

TODO: although the following works, the method to use bindings/linkings and $if_complete key in the source code is not ideal and subject to change.
WARNING: this function is experimental and is not subject to many tests.

## Session Setup

```python
from gpt_graph.core.components.input_initializer import InputInitializer

s = Session()
s.i0 = InputInitializer()
s.i1 = InputInitializer()
s.i2 = InputInitializer()
s.i3 = InputInitializer()
```

Four InputInitializer components (i0, i1, i2, i3) are created within the session.

## Custom Component Definition

```python
@component(
    step_type="list_to_node",
    input_schema={"x": {"dim": -1}, "z": {"dim": 0}, "y": {"dim": -1}},
)
def m0(x, y, z):
    return sum(x) + sum(y) + z

s.m0 = m0()
```

A custom component `m0` is defined with the following characteristics:
- Step type: "list_to_node"
- Input schema: 
  - `x`: variable dimension list
  - `z`: scalar value
  - `y`: variable dimension list
- Function: Sums all elements of `x`, all elements of `y`, and adds `z`
Note: if dimensions are -1, this means that the entire list of nodes (or their content) will be passed into the function.
if dimension are not -1, the list of nodes are split by node, and each node will be passed into one copy of function(or Component)

## Pipeline Definition

```python
s.p = s.i0 | [s.i3, s.i1, s.i2] | s.m0
```

The pipeline `p` is defined as follows:
- Start with `i0`
- Pass through a list containing `[i3, i1, i2]` (special syntax for parallel processing)
- End with `m0`

## Execution

```python
r = s.p.run(
    input_data={"i3": 1, "i1": 2, "i2": 3},
    params={"i0:input_format": "dict"}
)
```

The pipeline is executed with the following inputs:
- `i3` = 1
- `i1` = 2
- `i2` = 3
- `i0` is set to use a dictionary input format

## Execution Steps

1. `i0` processes the input dictionary
2. The list `[i3, i1, i2]` is processed in parallel:
   - `i3` outputs 1
   - `i1` outputs 2
   - `i2` outputs 3
3. `m0` receives the outputs as `x=1`, `y=2`, `z=3`
4. `m0` calculates: `1 + 2 + 3 = 6`

## Result

The final output of the pipeline is 6.

## Note on Special Syntax

The square brackets `[...]` in the pipeline definition `[s.i3, s.i1, s.i2]` indicate parallel processing of these components. This allows multiple inputs to be processed simultaneously and passed to the next component in the pipeline.


