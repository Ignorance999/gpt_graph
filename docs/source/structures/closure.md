# Closure

The `Closure` class is the foundation for both `Component` and `Session` classes, managing hierarchical relationships in complex structures.


## 1. Contains

- **`Closure.contains`**: A list holding references to child Components or Pipelines.
- Components are added to the hierarchy through operations like `|` (pipeline composition) or direct assignment.

## 2. Clones

- **`Closure.clones`**: A list that holds references to all `Closure` instances generated by the `Closure.clone()` method.

## 3. Naming System

The naming system uses three types of names:

- **`full_name`**: Complete path in the hierarchy
- **`base_name`**: Original name of the component
- **`name`**: Component's name, potentially with an index

### Naming Convention

- Components in Pipelines are assigned an index (lid) when contained within other components.
- The `full_name` uses semicolons (`;`) to represent the containment hierarchy.
- The `name` may include an index (e.g., "f4.0") when the component is contained within a pipeline.

### Example

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

# Naming examples
print("s3 full_name:", s3.full_name)                 # Output: Session
print("s3.p6 full_name:", s3.p6.full_name)           # Output: p6
print("s3.p6.contains[1] full_name:", s3.p6.contains[1].full_name)  # Output: p6;f4.0
print("s3.p3 full_name:", s3.p3.full_name)           # Output: p3
print("s3.p3.contains[1] full_name:", s3.p3.contains[1].full_name)  # Output: p3;p6.0
```

### Naming Table

| Component         | full_name | base_name | name    |
|-------------------|-----------|-----------|---------|
| s3                | Session   | Session   | Session |
| s3.p6             | p6        | p6        | p6      |
| s3.p6.contains[1] | p6;f4.0   | f4        | f4.0    |
| s3.p3             | p3        | p3        | p3      |
| s3.p3.contains[1] | p3;p6.0   | p6        | p6.0    |

## 4. Parameters 

- **`set_params()`**: Manually set parameters using a hierarchical syntax.
- **`load_params()`**: Load parameters from TOML or Python files.
- **`set_placeholders()`**: Manage placeholder values for parameters.

You can check more on [parameters](parameters.md) page

### Parameter Setting Syntax

- Use `;` for containment relationships and `:` for parameter keys.
- Example: `{'pipeline;component:param_key': param_value}`

## 5. Recursive Operations (for debugging)

- **`get_all_cps()`**: Retrieve all components in the hierarchy.
- **`get_rel_graph()`**: Generate relational graphs of the component structure.
- **`refresh_full_name()`**: Update names throughout the hierarchy.

## 6. Configuration and Serialization

- **`params_to_toml()`**: Convert parameters to TOML format.
- **`save_elements()`**: Serialize and save various elements like nodes or steps.
