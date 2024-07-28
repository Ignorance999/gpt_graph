# tutorial 4 how to use parameters

## Overview

Note: you can refer to test/test_pipeline.py -> test_5_pipeline_composition()

Note: In order to run it, you need to set up params. go to 
1. config/test_params.demo.toml -> change that to config/test_params.toml
2. config/env.demo.toml -> change that to env.toml, modify the file paths

This explains how params are set in the pipeline.


## Pipeline Structure
```python
from gpt_graph.tests.components.test_pp import test_pp

p = test_pp()

s5 = Session()
s5.p = p

s5.p2 = s5.p | s5.p

r3 = s5.p2.run(input_data=10)
```

The `test_pp` class is defined as follows:

```python
class test_pp(Pipeline):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.f5 = f5()
        self.f4 = f4()
        self.Testf = Testf()
        self | f5() | f4() | Testf()
```

This pipeline consists of three components: `f5`, `f4`, and `Testf`, connected in sequence.

## Component Definitions

### f4 Component

```python
@component(step_type="node_to_list")
def f4(x, y=1):
    return x + y, x - y
```

`f4` takes an input `x` and a parameter `y` (default 1), returning a list of two values: `x + y` and `x - y`.

### f5 Component

```python
@component(step_type="list_to_node")
def f5(x):
    return np.sum(x)
```

`f5` takes a list input `x` and returns the sum of its elements.

### Testf Component

```python
class Testf(Component):
    step_type = "node_to_node"
    input_schema = {"x": {"type": Any}}
    output_schema = {"result": {"type": Any}}
    output_format = "plain"

    @staticmethod
    def run(x, y):
        result = x + y
        return result
```

`Testf` adds the input `x` to a parameter `y` and returns the result.

## Parameter Setting

Parameters are set using a configuration file. The relevant parts are:

```ini
# Pipeline-wise parameters
y = 5

# Component-specific parameters
[Testf]
y = 2

```

### Priority

- The component-specific parameter `[Testf] y = 2` has higher priority than the pipeline-wise parameter `y = 5`.
- This means that for the `Testf` component, `y = 2` will be used instead of `y = 5`.


## Number Generation and Result Explanation

Calculation of r3 = [24, 14, 14, 4]

Starting with initial input 10:

1. f5(10) = 10 (passes unchanged)

2. f4(10, y=5) = [15, 5]
   (10 + 5 = 15, 10 - 5 = 5)

3. For 15:
   Testf(15, y=2) = 17
   f5(17) = 17
   f4(17, y=5) = [22, 12]
   Testf(22, y=2) = 24  <-- First element of the result
   Testf(12, y=2) = 14  <-- Second element of the result

4. For 5:
   Testf(5, y=2) = 7
   f5(7) = 7
   f4(7, y=5) = [12, 2]
   Testf(12, y=2) = 14  <-- Third element of the result
   Testf(2, y=2) = 4    <-- Fourth element of the result

Therefore, the final result is [24, 14, 14, 4].

## Key Points

1. The pipeline `p` is executed twice due to the structure `s5.p2 = s5.p | s5.p`.
2. `f4` always uses `y=5` (pipeline-wise parameter), while `Testf` uses `y=2` (component-specific parameter with higher priority).
3. The `f4` component returns two values each time, which are then processed separately by `Testf`.
4. The final result is a list containing the outputs from various stages of the second pass through the pipeline.
